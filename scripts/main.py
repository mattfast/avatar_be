import time

import requests

from dbs.mongo import mongo_read
from run_inference import generate_all_images
from train_model import check_job_status, post_request


def run_training_job_script():
    all_users = mongo_read("Users", {"images_uploaded": True}, find_many=True)
    for user in all_users:
        user_id = user.get("user_id")
        training_job = mongo_read("UserTrainingJobs", {"user_id": user_id})
        if training_job is None:
            post_request(user_id)


def check_jobs():
    while True:
        check_job_status()


def package_model_start():
    while True:
        all_completed_jobs = mongo_read(
            "UserTrainingJobs", {"training_status": "success"}, find_many=True
        )
        for job in all_completed_jobs:
            upload_status = job.get("upload_status", None)
            user_id = job.get("user_id")
            if upload_status is not None and upload_status != "failure":
                continue
            print(f"Sending package request for user_id {user_id}")
            # Send package request to next EC2 instance
            res = requests.post(f"https://milk-be.com/upload-model/{user_id}")
            print(res.text)


def infer():
    while True:
        all_completed_uploads = mongo_read(
            "UserTrainingJobs", {"upload_status": "success"}, find_many=True
        )
        for job in all_completed_uploads:
            user_id = job.get("user_id")
            generation_status = job.get("generation_status", None)

            if generation_status is None or generation_status == "failure":
                print(f"Generating Images for {user_id}")
                # Send image generation query
                res = requests.post(f"https://milk-be.com/run-inference/{user_id}")
                print(res.text)

            while True:
                curr_job = mongo_read(
                    "UserTrainingJobs",
                    {"user_id": user_id},
                )
                curr_status = curr_job.get("generation_status", None)
                print(f"{curr_status} generation status for job with user_id {user_id}")
                if curr_status == "success" or curr_status == "failure":
                    break
