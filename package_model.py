import json
import os
import shutil
import tarfile
from datetime import datetime, timezone
from pathlib import Path

import boto3
import requests
import sagemaker

from dbs.mongo import mongo_read, mongo_upsert

# Count number of directories in path

dreamlook_api_key = "dl-DBF11F7B34E04537B0EE54DF15C07255"
headers = {
    "content-type": "application/json",
    "authorization": f"Bearer {dreamlook_api_key}",
}

model_folder_name = "packaged_models"


sagemaker_session = sagemaker.Session(
    boto_session=boto3.Session(
        region_name="us-east-2",
    )
)
bucket = sagemaker_session.default_bucket()
prefix = "stable-diffusion-mme"


def package_model(user_id):
    try:
        number_of_folders = len(next(os.walk(model_folder_name))[1])
    except:
        number_of_folders = 0

    if number_of_folders >= 10:
        print(f"Number of folders {number_of_folders}")
        return

    training_job = mongo_read("UserTrainingJobs", {"user_id": user_id})
    url = training_job.get("job_url", None)

    if url is None:
        print(f"URL IS NONE")
        return

    # Upsert Directory to Say Model Has been uploaded
    mongo_upsert(
        "UserTrainingJobs",
        {"user_id": user_id},
        {"upload_status": "started"},
    )

    try:
        print("ENTERING LOOP")
        res2 = requests.get(url, headers=headers)
        loaded_resp = json.loads(res2.text)
        model_url = loaded_resp["dreambooth_result"]["checkpoints"][0]["url"]
        print(f"Got Model URL {model_url}")

        user_name = user_id
        base_path = Path(model_folder_name) / user_name
        artifacts_folder = Path(model_folder_name) / "artifacts"

        print(f"Creating Base Path {str(base_path)}")
        base_path.mkdir(parents=True, exist_ok=True)

        model_version_path = base_path / "1"
        print(f"Creating Model Version Path {str(model_version_path)}")
        model_version_path.mkdir(parents=True, exist_ok=True)

        print("Writing config.pbtxt file")
        # Write config.pbtxt
        to_write = open(base_path / "config.pbtxt", "w+")
        to_write.write(f'name: "{user_name}"\n')
        to_write.write(open(artifacts_folder / "config.pbtxt", "r").read())
        to_write.close()

        print("Writing model.py file")
        # Write Model.PY
        py_file_write = open(model_version_path / "model.py", "w+")
        py_file_write.write(open(artifacts_folder / "model.py", "r").read())
        py_file_write.close()

        print("Loading Safetensors file")
        # Write safetensors file
        response = requests.get(model_url, stream=True)
        with open(model_version_path / "custom_model.safetensors", mode="wb") as file:
            for chunk in response.iter_content(chunk_size=10 * 1024):
                file.write(chunk)

        print("Writing tar file")
        save_file_name = f"packaged_models/{user_id}.tar.gz"
        with tarfile.open(save_file_name, "w:gz") as tar:
            tar.add(base_path, arcname=os.path.basename(base_path))

        print("Uploading file to S3")
        sagemaker_session.upload_data(
            path=save_file_name, bucket=bucket, key_prefix=prefix
        )

        print("Removing Directories")
        shutil.rmtree(base_path, ignore_errors=True)
        os.remove(save_file_name)

        # Upsert Directory to Say Model Has been uploaded
        mongo_upsert(
            "UserTrainingJobs",
            {"user_id": user_id},
            {"upload_status": "success", "uploaded_time": datetime.now(timezone.utc)},
        )
    except:
        # Upsert Directory to Say Model Has been uploaded
        print("JUST EXCEPTED")
        mongo_upsert(
            "UserTrainingJobs",
            {"user_id": user_id},
            {"upload_status": "failure"},
        )
