import base64
import io
import json
import random
import time
from io import BytesIO

import boto3
from PIL import Image

from constants import (
    boy_styles,
    default_negative,
    full_boy_styles,
    full_girl_styles,
    girl_styles,
)
from dbs.mongo import mongo_read, mongo_upsert

runtime_sm_client = boto3.client(
    region_name="us-east-2",
    service_name="sagemaker-runtime",
)

s3 = boto3.client(
    region_name="us-east-1",
    service_name="s3",
)


class StableDiffusionRunConfig:
    def __init__(
        self,
        style: str,
        prompt: str,
        negative_prompt: str = default_negative,
        strength: float = 0.8,
        steps: int = 70,
        scale: float = 7.5,
    ):
        self.style = style
        self.prompt = prompt
        self.negative_prompt = negative_prompt
        self.strength = strength
        self.steps = steps
        self.scale = scale
        if self.style == "pixar":
            self.strength = 0.9
            self.scale = 10
            self.steps = 90


# helper functions to encode and decode images
def encode_image(image):
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    img_str = base64.b64encode(buffer.getvalue())

    return img_str


def decode_image(img):
    buff = BytesIO(base64.b64decode(img.encode("utf8")))
    image = Image.open(buff)
    return image


def run_sd_config(
    runtime_sm_client,
    model_name,
    run_config,
    img_to_use,
    endpoint_name: str = "stable-diffusion-mme-ep-2023-09-28-00-43-55",
    num_runs: int = 1,
):
    for i in range(num_runs):
        input_image = encode_image(img_to_use).decode("utf8")

        inputs = dict(
            prompt=run_config.prompt,
            negative_prompt=run_config.negative_prompt,
            image=input_image,
            gen_args=json.dumps(
                dict(
                    num_inference_steps=run_config.steps,
                    strength=run_config.strength,
                    guidance_scale=run_config.scale,
                )
            ),
        )

        payload = {
            "inputs": [
                {"name": name, "shape": [1, 1], "datatype": "BYTES", "data": [data]}
                for name, data in inputs.items()
            ]
        }

        image = None
        while True:
            try:
                print(
                    f"Generating Image {i} for {model_name} with {run_config.style} style...."
                )
                response = runtime_sm_client.invoke_endpoint(
                    EndpointName=endpoint_name,
                    ContentType="application/octet-stream",
                    Body=json.dumps(payload),
                    TargetModel=model_name,
                )
                output = json.loads(response["Body"].read().decode("utf8"))["outputs"]
                image = decode_image(output[0]["data"][0])
                break
            except Exception as e:
                if "ModelError" in str(e):
                    print("ERROR")
                    time.sleep(2)
                    continue
                print(str(e))
                break

        return image


def load_prompts(file_name):
    with open(file_name, "r") as f:
        prompts_file = f.read()
    prompts_list = prompts_file.split("\n")
    return [
        prompt.split("||")[0].strip() for prompt in prompts_list if prompt.strip() != ""
    ]


def construct_config_from_prompt_style(prompt: str, style_map: dict, style: str):
    if style_map[style].get("no_prompt", False):
        full_prompt = style_map[style]["full_prompt"]
    else:
        full_prompt = style_map[style]["start"] + prompt + style_map[style]["end"]
    return StableDiffusionRunConfig(style=style, prompt=full_prompt)


def generate_all_images(
    user_id, endpoint_name: str = "stable-diffusion-mme-ep-2023-09-28-00-43-55"
):
    print("ENTERED GENERATION")
    user = mongo_read("Users", {"user_id": user_id})
    user_prefs = user.get(
        "image_config", ["warrior", "athlete", "magic", "princess", "king", "cowboy"]
    )
    replace_dict = {"magical": "magic"}
    for i, pref in enumerate(user_prefs):
        if pref in replace_dict:
            user_prefs[i] = replace_dict[pref]

    print("READ USER INGO")

    gender = user.get("gender", "girl").strip().lower()

    prefix = "female_"
    style_map = girl_styles
    extra_styles = full_girl_styles
    starter_file = f"prompt_info/female_starter_map.json"
    if gender == "boy":
        prefix = ""
        style_map = boy_styles
        extra_styles = full_boy_styles
        starter_file = f"prompt_info/starter_map.json"

    print(f"LOADING STARTER MAP {starter_file}")

    model_name = f"{user_id}.tar.gz"

    bucket_name = "dopple-generated"
    actual_choice_list = [f"{choice}_prompts" for choice in user_prefs]

    with open(starter_file, "r") as f:
        starter_map = json.load(f)

    print("LOADED STARTER MAP FILE")

    mongo_upsert(
        "UserTrainingJobs", {"user_id": user_id}, {"generation_status": "started"}
    )

    try:
        # Generate 10 images for the user
        for i in range(10):
            key = f"{user_id}/profile_{i}.png"
            print("CHOOSING RANDOM CATEGORY FROM LIST")
            choice = random.choice(actual_choice_list)
            style_options = list(starter_map[choice].keys()) + extra_styles

            print("CHOOSING RANDOM STYLE FROM LIST")
            style = random.choice(style_options)

            print("LOADING PROMPTS FROM LIST")
            all_prompts = load_prompts(f"prompt_info/{prefix}{choice}.txt")
            chosen_prompt = random.choice(all_prompts)

            print("CHOOSING RANDOM PROMPT AND CONSTRUCTING CONFIG")
            config = construct_config_from_prompt_style(chosen_prompt, style_map, style)

            # Random Extra styles not in the starter map
            if style in extra_styles:
                filter_to_use = "tester"
            else:
                filter_to_use = random.choice(list(starter_map[choice][style]))

            print("OPENING IMAGE")
            try:
                filter_image = Image.open(f"filters/tested/{filter_to_use}.jpeg")
            except:
                filter_image = Image.open(f"filters/tested/{filter_to_use}.jpg")

            image = run_sd_config(
                runtime_sm_client, model_name, config, filter_image, endpoint_name
            )

            in_mem_file = io.BytesIO()
            image.save(in_mem_file, format="JPEG")
            in_mem_file.seek(0)

            # Upload image to s3
            s3.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=in_mem_file,
                ContentType="image/jpeg",
            )
        mongo_upsert(
            "UserTrainingJobs", {"user_id": user_id}, {"generation_status": "success"}
        )
    except Exception as e:
        print("EXCEPTION GENERATED")
        print(e)
        mongo_upsert(
            "UserTrainingJobs", {"user_id": user_id}, {"generation_status": "failure"}
        )
