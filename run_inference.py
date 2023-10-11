import base64
import io
import json
import logging
import os
import random
import time
from io import BytesIO
from pathlib import Path
from typing import Optional
from uuid import uuid4

import boto3
from PIL import Image

from constants import (
    boy_styles,
    default_negative,
    extra_boy_styles,
    extra_girl_styles,
    girl_styles,
    random_animal_styles,
)
from dbs.mongo import mongo_count, mongo_read, mongo_upsert
from messaging import TextType, send_message

runtime_sm_client = boto3.client(
    region_name="us-east-2",
    service_name="sagemaker-runtime",
)

s3 = boto3.client(
    region_name="us-east-1",
    service_name="s3",
)

logging.basicConfig(level=logging.INFO)


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

    def to_dict(self) -> dict:
        return {
            "full_prompt": self.prompt,
            "style": self.style,
            "negative_prompt": self.negative_prompt,
            "strength": self.strength,
            "scale": self.scale,
            "steps": self.steps,
        }


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


ENV_STR = "/tmp/conda/sd_env.tar.gz"  # With this error -> Load ENV, wait and continue
READ_TIMEOUT_STR = "timeout on endpoint URL"  # Endpoint is down. Move to the next endpoint (or wait 10 minutes and retry)
MAX_RETRIES_STR = "(reached max retries: 4)"  # Endpoint is down. Move to the next endpoint (or wait 10 minutes and retry)

# For Variant Error
GENERIC_EXCEPTION = (
    "exception"  # First error on max retries, model has not loaded completely yet
)
VARIANT_STR = "Variant"  # Second error on max retries, model is starting to load
MODEL_ERROR = "ModelError"  # other generic errors, just retry after 10 seconds


def switch_to_next_endpoint(curr_endpoint: str) -> None:
    endpoint_to_use = mongo_read("Endpoints", {"endpoint_name": curr_endpoint})

    num_endpoints = mongo_count("Endpoints")
    next_endpoint_id = (endpoint_to_use.get("num_id", 0) + 1) % num_endpoints

    logging.info(f"Changed NEXT ENDPOINT TO {next_endpoint_id}")

    # Update current endpoint to not be used
    mongo_upsert("Endpoints", {"endpoint_name": curr_endpoint}, {"in_use": False})
    mongo_upsert("Endpoints", {"num_id": next_endpoint_id}, {"in_use": True})
    return


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
                except_str = str(e)
                logging.info(except_str)
                if ENV_STR in except_str:
                    logging.info("ENV LOADING ERROR")
                    logging.info(e)
                    backup_setup(runtime_sm_client, endpoint_name)
                    time.sleep(40)
                    continue
                elif READ_TIMEOUT_STR in except_str or MAX_RETRIES_STR in except_str:
                    logging.info("REQUEST PROCESSING ERROR")
                    logging.info(e)
                elif MODEL_ERROR in except_str:
                    logging.info("Generic Model Error")
                    logging.info(e)
                    time.sleep(5)
                    continue
                else:
                    logging.info("Another Error")
                    logging.info(e)

                return None

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


def backup_setup(runtime_sm_client, endpoint_name: str):
    payload = {
        "inputs": [
            {
                "name": "TEXT",
                "shape": [1],
                "datatype": "BYTES",
                "data": ["hello"],  # dummy data not used by the model
            }
        ]
    }

    response = runtime_sm_client.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType="application/octet-stream",
        Body=json.dumps(payload),
        TargetModel="setup_conda.tar.gz",
    )
    logging.info(response)


def get_current_endpoint_to_use() -> Optional[str]:
    endpoint_to_use = mongo_read("Endpoints", {"in_use": True})

    if endpoint_to_use is None:
        return None
    return endpoint_to_use.get("endpoint_name", None)


def log_generation_info(
    user_id: str, profile_id: int, config: StableDiffusionRunConfig, extra_info: dict
):
    """Log generation information to Mongo."""
    dict_to_upsert = {
        "user_id": user_id,
        "profile_id": profile_id,
        **config.to_dict(),
        **extra_info,
    }
    mongo_upsert(
        "GenerationInfo", {"user_id": user_id, "profile_id": profile_id}, dict_to_upsert
    )


def generate_all_images(user_id):
    mongo_upsert(
        "UserTrainingJobs", {"user_id": user_id}, {"generation_status": "started"}
    )

    logging.info("ENTERED GENERATION")
    user = mongo_read("Users", {"user_id": user_id})
    user_prefs = user.get(
        "image_config", ["warrior", "athlete", "magic", "princess", "king", "cowboy"]
    )
    replace_dict = {"magical": "magic"}
    for i, pref in enumerate(user_prefs):
        if pref in replace_dict:
            user_prefs[i] = replace_dict[pref]

    logging.info("GETTING ENDPOINT")
    endpoint_name = get_current_endpoint_to_use()
    logging.info(f"GOT ENDPOINT {endpoint_name}")

    if endpoint_name is None:
        logging.info("NO ENDPOINT NAME")
        mongo_upsert(
            "UserTrainingJobs", {"user_id": user_id}, {"generation_status": "failure"}
        )
        return

    logging.info("READ USER INFO")

    gender = user.get("gender", "girl").strip().lower()

    curr_directory = "/home/ubuntu/avatar_be"

    prefix = "female_"
    style_map = girl_styles
    extra_styles = extra_girl_styles
    starter_file = Path(f"{curr_directory}/prompt_info/female_starter_map.json")
    if gender == "boy":
        prefix = ""
        style_map = boy_styles
        extra_styles = extra_boy_styles
        starter_file = Path(f"{curr_directory}/prompt_info/starter_map.json")

    logging.info(f"LOADING STARTER MAP {starter_file}")

    model_name = f"{user_id}.tar.gz"

    bucket_name = "dopple-generated"
    actual_choice_list = [f"{choice}_prompts" for choice in user_prefs]

    with open(starter_file, "r") as f:
        starter_map = json.load(f)

    logging.info("LOADED STARTER MAP FILE")

    funny_profile_styles = ["stick_figure"] + extra_styles

    # Profile of funny profiles that have been generated so far
    funny_profile_style_dict = {}
    MAX_NUM_FUNNY_PROFILES = 2

    try:
        num_funny_styles = 0
        has_animal_style = False
        # Generate 10 images for the user
        for i in range(25):
            key = f"{user_id}/profile_{i}.png"
            logging.info("CHOOSING RANDOM CATEGORY FROM LIST")
            category = random.choice(actual_choice_list)

            while True:
                # always generate a funny style at least once
                if i == 9 and num_funny_styles == 0:
                    style_options = funny_profile_styles
                else:
                    style_options = list(starter_map[category].keys()) + extra_styles

                logging.info("CHOOSING RANDOM STYLE FROM LIST")
                style = random.choice(style_options)

                # Parse through funny styles
                is_funny_style = style in funny_profile_styles
                if is_funny_style:
                    is_animal_style = style in random_animal_styles
                    # Don't generate too many profiles
                    # Don't generate the first profile as funny
                    # Don't regenerate a funny profile that has already been generated
                    # Only generat one animal style
                    if num_funny_styles >= MAX_NUM_FUNNY_PROFILES:
                        continue
                    elif i == 0:
                        continue
                    elif style in funny_profile_style_dict:
                        continue
                    elif is_animal_style and has_animal_style:
                        continue

                    num_funny_styles += 1
                    funny_profile_style_dict[style] = True
                    if is_animal_style and not has_animal_style:
                        has_animal_style = True
                    break
                else:
                    break

            logging.info("LOADING PROMPTS FROM LIST")
            all_prompts = load_prompts(
                Path(f"{curr_directory}/prompt_info/{prefix}{category}.txt")
            )
            chosen_prompt = random.choice(all_prompts)

            logging.info("CHOOSING RANDOM PROMPT AND CONSTRUCTING CONFIG")
            config = construct_config_from_prompt_style(chosen_prompt, style_map, style)

            # Random Extra styles not in the starter map
            if style in extra_styles:
                filter_to_use = "tester"
            else:
                filter_to_use = random.choice(list(starter_map[category][style]))

            logging.info("OPENING IMAGE")
            try:
                filter_image = Image.open(
                    f"{curr_directory}/filters/tested/{filter_to_use}.jpeg"
                )
            except:
                filter_image = Image.open(
                    f"{curr_directory}/filters/tested/{filter_to_use}.jpg"
                )

            logging.info("OPENED IMAGE")

            logging.info(
                f"Generating Image {i} for {model_name} with {config.style} style...."
            )
            image = run_sd_config(
                runtime_sm_client, model_name, config, filter_image, endpoint_name
            )

            if image is None:
                logging.info(
                    f"Inference for user id {user_id} failed, switching to another endpoint"
                )
                switch_to_next_endpoint(curr_endpoint=endpoint_name)
                mongo_upsert(
                    "UserTrainingJobs",
                    {"user_id": user_id},
                    {"generation_status": "failure"},
                )
                return

            in_mem_file = io.BytesIO()
            image.save(in_mem_file, format="JPEG")
            in_mem_file.seek(0)

            # Upload Profile Info to mongo
            log_generation_info(
                user_id,
                i,
                config,
                {
                    "category": category,
                    "base_prompt": chosen_prompt,
                    "filter": filter_to_use,
                },
            )

            # Upload image to s3
            s3.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=in_mem_file,
                ContentType="image/jpeg",
            )

        logging.info(f"SUCCESSFULLY GENERATED IMAGES for {user_id}. UPDATING.")
        mongo_upsert(
            "UserTrainingJobs", {"user_id": user_id}, {"generation_status": "success"}
        )

        # update user entry
        mongo_upsert(
            "Users",
            {"user_id": user_id},
            {"images_generated": True, "primary_image": 0},
        )
        logging.info(f"UPDATED USER INFO for {user_id}. NOW SENDING TEXT")

        # notify user
        """
        text_id = str(uuid4())
        number = user.get("number", None)
        send_message(
            "🚨ALERT🚨 Your dopple is ready to view. Look here to see your options:",
            "+1" + number,
        )
        send_message(
            f"https://dopple.club/profile/${user_id}?t={text_id}",
            "+1" + number,
            message_type=TextType.ALERT,
            user_id=user_id,
            text_id=text_id,
            log=True,
        )
        """

        logging.info(f"SENDING MESSAGE to {user_id}")

    except Exception as e:
        logging.info("EXCEPTION GENERATED")
        logging.info(e)
        mongo_upsert(
            "UserTrainingJobs", {"user_id": user_id}, {"generation_status": "failure"}
        )
        return
