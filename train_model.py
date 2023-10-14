import json
import subprocess
import threading
import logging
from constants import PATH_PREFIX
import time

import boto3
import requests
from botocore.exceptions import ClientError

from dbs.mongo import mongo_read, mongo_upsert

logging.basicConfig(level=logging.INFO)

dreamlook_api_key = "dl-DBF11F7B34E04537B0EE54DF15C07255"
headers = {
    "content-type": "application/json",
    "authorization": f"Bearer {dreamlook_api_key}",
}


def create_presigned_url(bucket_name, object_name, expiration=36000):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    client = boto3.client(
        "s3",
        region_name="us-east-1",
    )
    try:
        response = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_name},
            ExpiresIn=expiration,
        )
    except ClientError as e:
        print(e)
        return None

    # The response contains the presigned URL
    return response


def create_urls_for_training(user_id: str):
    selfie_bucket = "dopple-selfies"
    urls = []
    object_name = [f"selfie-{i}-{user_id}.jpg" for i in range(5)]
    for obj in object_name:
        urls.append(create_presigned_url(selfie_bucket, obj))
    return urls


def post_request(user_id: str) -> None:
    """Post Request."""
    job_id = None
    urls = create_urls_for_training(user_id)
    while job_id is None:
        payload = {
            "image_urls": urls,
            "steps": 1200,
            "learning_rate": 0.000001,
            "instance_prompt": "photo of ukj person",
            "model_type": "sd-v1",
            "base_model": "stable-diffusion-v1-5",
            "crop_method": "center",
            "saved_model_format": "original",
            "saved_model_weights_format": "safetensors",
            "extract_lora": "disabled",
        }
        payload_str = json.dumps(payload)
        res = requests.post(
            "https://api.dreamlook.ai/dreambooth", data=payload_str, headers=headers
        )
        job_id = json.loads(res.text).get("job_id", None)

    job_url = f"https://api.dreamlook.ai/jobs/dreambooth/{job_id}"
    mongo_upsert(
        "UserTrainingJobs",
        {"user_id": user_id},
        {"training_status": "started", "job_url": job_url},
    )


def check_job_status():
    all_started_jobs = mongo_read(
        "UserTrainingJobs", {"training_status": "started"}, find_many=True
    )
    for job in all_started_jobs:
        user_id = job.get("user_id")
        job_url = job.get("job_url", None)
        if job_url is None:
            logging.info("ERROR: JOB Started with no URL")
            mongo_upsert(
                "UserTrainingJobs", {"user_id": user_id}, {"training_status": "failure"}
            )
            continue
        res2 = requests.get(job_url, headers=headers)
        loaded_resp = json.loads(res2.text)
        state = loaded_resp["state"]

        logging.info(f"User ID {user_id} is in state: {state}")
        if state == "failure":
            mongo_upsert(
                "UserTrainingJobs", {"user_id": user_id}, {"training_status": "failure"}
            )
            continue

        if state == "success":
            mongo_upsert(
                "UserTrainingJobs", {"user_id": user_id}, {"training_status": "success"}
            )


def check_job_until_finished(job_url, user_id):
    is_success = False
    # Update Mongo
    while not is_success:
        res2 = requests.get(job_url, headers=headers)
        loaded_resp = json.loads(res2.text)
        state = loaded_resp["state"]
        if state == "failure":
            mongo_upsert(
                "UserTrainingJobs", {"user_id": user_id}, {"training_status": "failure"}
            )
            return
        time.sleep(20)
        is_success = state == "success"
    logging.info("SUCCESS")
    mongo_upsert(
        "UserTrainingJobs", {"user_id": user_id}, {"training_status": "success"}
    )


def _exec_subprocess(cmd: str):
    """Executes subprocess and prints log to terminal while subprocess is running."""
    logging.info(subprocess.run('echo "$SHELL"', shell=True))
    logging.info(subprocess.run("which python3", shell=True))
    logging.info(subprocess.run("which modal", shell=True))
    logging.info(subprocess.run("modal --help", shell=True))
    # process = subprocess.Popen(
    #     [cmd],
    #     stdout=subprocess.PIPE,
    #     stderr=subprocess.STDOUT,
    #     shell=True,
    # )
    #
    # # TODO: Remove this. Will clutter Output
    # with process.stdout as pipe:
    #     for line in iter(pipe.readline, b""):
    #         line_str = line.decode()
    #         logging.info(f"{line_str}")
    #
    # if exitcode := process.wait() != 0:
    #     raise subprocess.CalledProcessError(exitcode,  cmd)


def launch_modal_training_command(user_id, upload_only: bool = False):
    urls = []
    if not upload_only:
        urls = create_urls_for_training(user_id)
    combined_urls = "\n".join(urls)

    prefix = PATH_PREFIX
    upload_only_str = "true" if upload_only else "false"

    cmd = " ".join([
        "modal",
        "run",
        f"{prefix}modal_dreambooth.py",
        f"--user={user_id}",
        f"--urls='{combined_urls}'",
        f"--upload-only={upload_only_str}",
    ])

    try:
        _exec_subprocess(cmd)
    except Exception as e:
        # Call failure
        logging.info("ERROR")
        logging.info(e)
