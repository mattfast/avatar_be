import os
from dataclasses import dataclass
from pathlib import Path

from modal import (
    Image,
    Mount,
    Secret,
    Stub,
    Volume,
    asgi_app,
    method,
)

assets_path = Path(__file__).parent / "assets"
stub = Stub(name="dream-booth-test")

GIT_SHA = "2c298300756fa7d8bf644852cffaebc5072f11f6"

image = (
    Image.debian_slim(python_version="3.11")
    .pip_install(
        "accelerate",
        "ftfy",
        "smart_open",
        "transformers>=4.25.1",
        "torch",
        "torchvision",
        "triton",
        "certifi",
        "Jinja2",
        "pymongo",
        "scipy",
        "safetensors",
        "tensorboard"
    )
    .pip_install("xformers==0.0.22", pre=True)
    .pip_install("bitsandbytes", pre=True)
    .apt_install("git")
    # Perform a shallow fetch of just the target `diffusers` commit, checking out
    # the commit in the container's current working directory, /root. Then install
    # the `diffusers` package.
    .run_commands(
        "cd /root && git init .",
        "cd /root && git remote add origin https://github.com/ShivamShrirao/diffusers.git",
        f"cd /root && git fetch --depth=1 origin {GIT_SHA} && git checkout {GIT_SHA}",
        "cd /root && pip install -e .",
    )
)

s3_upload_image = (
    Image.debian_slim(python_version="3.11")
    .pip_install(
        "boto3",
        "sagemaker",
    )
)

volume = Volume.persisted("finetune-volume")
MODEL_DIR = Path("/model")
stub.volume = volume


IMG_PATH = Path("/img")


def load_images(image_urls):
    import PIL.Image
    from smart_open import open

    os.makedirs(IMG_PATH, exist_ok=True)
    for ii, url in enumerate(image_urls):
        with open(url, "rb") as f:
            image = PIL.Image.open(f)
            image.save(IMG_PATH / f"{ii}.png")
    print("Images loaded.")

    return IMG_PATH


@dataclass
class TrainConfig():
    """Configuration for the finetuning step."""

    # locator for plaintext file with urls for images of target instance
    instance_example_urls_file: str = str(
        Path(__file__).parent / "instance_example_urls.txt"
    )

    # identifier for pretrained model on Hugging Face
    model_name: str = "runwayml/stable-diffusion-v1-5"
    vae_name: str = "stabilityai/sd-vae-ft-mse"

    # Hyperparameters/constants from the huggingface training example
    resolution: int = 512
    train_batch_size: int = 2
    gradient_accumulation_steps: int = 1
    learning_rate: float = 1e-6
    lr_scheduler: str = "constant"
    lr_warmup_steps: int = 0
    max_train_steps: int = 1000
    num_class_images: int = 300


@stub.function(
    image=image,
    gpu="A100",  # finetuning is VRAM hungry, so this should be an A100
    volumes={
        str(
            MODEL_DIR
        ): volume,  # fine-tuned model will be stored at `MODEL_DIR`
    },
    timeout=1800,  # 30 minutes
    secret=Secret.from_name("mongo")
)
def train(instance_example_urls, user_id):
    import subprocess
    import pymongo
    import certifi
    import sys
    from accelerate.utils import write_basic_config

    mongo_key = os.environ["MONGO_KEY"]
    mongo_connection_string = f"mongodb+srv://matthew:{mongo_key}@cluster0.4exrr9f.mongodb.net/?retryWrites=true&w=majority"
    try:
        client = pymongo.MongoClient(mongo_connection_string, tlsCAFile=certifi.where())
    except pymongo.errors.ConfigurationError:
        print(
            "An Invalid URI host error was received. Is your Atlas host name correct in your connection string?"
        )
        sys.exit(1)
    else:
        print("MONGO CLIENT")
        print(client)
    mongo_db = client["DoppleProd"]

    def mongo_upsert(collection, query, update, update_many: bool = False):
        try:
            if not update_many:
                result = mongo_db[collection].update_one(
                    query, {"$set": update}, upsert=True
                )
            else:
                result = mongo_db[collection].update_many(
                    query, {"$set": update}, upsert=True
                )
        except pymongo.errors.OperationFailure:
            print("MONGO UPDATE ERROR")
            print(f"Collection: {collection}")
            print(f"Query Param: {query}")
            print(f"Update Param: {update}")
            result = None

        print(result)
        return result

    # set up runner-local image and shared model weight directories
    img_path = load_images(instance_example_urls)
    output_dir = MODEL_DIR/f"{user_id}_outputs"
    os.makedirs(output_dir, exist_ok=True)

    print(f"OUTPUT DIR IS {str(output_dir)}")

    # Set up train config
    config = TrainConfig()

    # set up hugging face accelerate library for fast training
    write_basic_config(mixed_precision="fp16")

    # define the training prompt
    instance_phrase = f"photo of ukj person"

    def _exec_subprocess(cmd: list[str]):
        """Executes subprocess and prints log to terminal while subprocess is running."""
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        with process.stdout as pipe:
            for line in iter(pipe.readline, b""):
                line_str = line.decode()
                print(f"{line_str}", end="")

        if exitcode := process.wait() != 0:
            raise subprocess.CalledProcessError(exitcode, "\n".join(cmd))

    # run training -- see huggingface accelerate docs for details
    print("launching dreambooth training script")
    _exec_subprocess(
        [
            "accelerate",
            "launch",
            "examples/dreambooth/train_dreambooth.py",
            f"--pretrained_model_name_or_path={config.model_name}",
            "--train_text_encoder",  # needs at least 16GB of GPU RAM.
            f"--pretrained_vae_name_or_path={config.vae_name}",
            f"--instance_data_dir={img_path}",
            f"--output_dir={output_dir}",
            "--class_data_dir=examples/dreambooth/person",
            "--with_prior_preservation",
            "--prior_loss_weight=1.0",
            f"--instance_prompt='{instance_phrase}'",
            "--class_prompt='photo of person'",
            f"--resolution={config.resolution}",
            f"--train_batch_size={config.train_batch_size}",
            f"--gradient_accumulation_steps={config.gradient_accumulation_steps}",
            "--gradient_checkpointing",
            "--use_8bit_adam",
            "--mixed_precision=fp16",
            f"--learning_rate={config.learning_rate}",
            f"--lr_scheduler={config.lr_scheduler}",
            f"--lr_warmup_steps={config.lr_warmup_steps}",
            f"--num_class_images={config.num_class_images}",
            f"--max_train_steps={config.max_train_steps}"
        ]
    )

    mongo_upsert("UserTrainingJobs", {"user_id": user_id}, {"modal_training_status": "success"})
    # The trained model artefacts have been output to the volume mounted at `MODEL_DIR`.
    # To persist these artefacts for use in future inference function calls, we 'commit' the changes
    # to the volume.
    stub.volume.commit()


@stub.function(
    image=s3_upload_image,
    volumes={
    str(
        MODEL_DIR
        ): volume,  # fine-tuned model will be stored at `MODEL_DIR`
    },
    timeout=1800,  # 30 minutes
    secret=Secret.from_name("my-aws-secret")
)
def upload_to_s3(ids_to_parse: list[str]):
    import boto3
    import os
    import shutil
    import tarfile

    s3 = boto3.resource('s3', region_name="us-east-1")

    # Create zip and upload to s3
    for id in ids_to_parse:
        print(f"Fetching new model for {id}")
        base_path = MODEL_DIR / f"{id}_outputs/"
        save_file_name = MODEL_DIR / f"{id}.tar.gz"
        with tarfile.open(save_file_name, "w:gz") as tar:
            tar.add(base_path, arcname=os.path.basename(base_path))

        print("Uploading model")
        s3.meta.client.upload_file(save_file_name, 'uploaded-models', f"{id}.tar.gz")
        print("Removing Directories and files")
        shutil.rmtree(base_path, ignore_errors=True)
        os.remove(save_file_name)

        # Commit volume changes
        stub.volume.commit()


import sys
sys.path.append("/home/ubuntu/avatar_be/")


@stub.local_entrypoint()
def run(urls: str, user: str):
    parsed_urls = [url.strip() for url in urls.split("\n")]
    try:
        from dbs.mongo import mongo_upsert

        try:
            mongo_upsert("UserTrainingJobs", {"user_id": user}, {"modal_training_status": "started"})
            train.remote(parsed_urls, user)
            upload_to_s3.remote([user])
        except:
            print("FAILED")
            mongo_upsert("UserTrainingJobs", {"user_id": user}, {"modal_training_status": "failure"})
    except Exception as e:
        print(f"Exception raised: {e}")