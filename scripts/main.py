import argparse
import json
import os
import subprocess
import sys
import threading
import time
from copy import deepcopy
from typing import Optional
import logging
import requests

sys.path.append("/Users/akashsamant/imagegen/avatar_be")

from dbs.mongo import mongo_read
from train_model import check_job_status, launch_modal_training_command, post_request

parser = argparse.ArgumentParser()

logging.basicConfig(level=logging.INFO)

def run_training_job_script():
    all_users = mongo_read("Users", {"images_uploaded": True}, find_many=True)
    for user in all_users:
        user_id = user.get("user_id")
        training_job = mongo_read("UserTrainingJobs", {"user_id": user_id})
        if training_job is None:
            print(f"POSTING TRAINING REQUEST FOR {user_id}")
            post_request(user_id)
            continue
        training_status = training_job.get("training_status")
        if training_status == "failure":
            print(f"POSTING TRAINING REQUEST FOR PREVIOUSLY FAILED {user_id}")
            post_request(user_id)


def run_modal_training_script(max_users: int):
    users_to_train = mongo_read("Users", {"images_uploaded": True}, find_many=True)
    num_trained = 0
    logging.info(f"MAX USERS: {max_users}")
    for user in users_to_train:
        if num_trained >= max_users:
            break
        logging.info(user)
        user_id = user.get("user_id")
        training_job = mongo_read("UserTrainingJobs", {"user_id": user_id})
        if training_job is None:
            logging.info(f"POSTING TRAINING REQUEST FOR {user_id}")
            post_thread = threading.Thread(
                target=launch_modal_training_command, args=[user_id, False]
            )
            post_thread.start()
            continue

        training_status = training_job.get("modal_training_status", None)
        if training_status == "failure":
            logging.info(f"POSTING TRAINING REQUEST FOR PREVIOUSLY FAILED {user_id}")
            post_thread = threading.Thread(
                target=launch_modal_training_command, args=[user_id, False]
            )
            post_thread.start()
            continue

        s3_upload_status = training_job.get("modal_s3_upload_status", None)
        if training_status == "success" and s3_upload_status == "failure":
            logging.info(f"POSTING THREAD FOR UPLOAD FOR {user_id}")
            post_thread = threading.Thread(
                target=launch_modal_training_command, args=[user_id, True]
            )
            post_thread.start()
        num_trained += 1
    logging.info("FINISHED PROCESSING NEXT MODAL JOBS")


def run_training_job_script_loop():
    while True:
        run_training_job_script()


def check_jobs():
    while True:
        check_job_status()


# ips_to_use = [
#     "54.234.2.188",
#     "3.80.54.100",
#     "54.175.164.253",
#     "3.236.123.16",
#     "3.91.229.64",
#     "3.227.16.23",
#     "54.160.89.223",
#     "100.25.134.210",
#     "34.205.31.110",
#     "3.86.59.61",
# ]


ips_to_use = [
    "3.83.253.250",
    "100.26.219.225",
    "54.83.138.37",
    "34.229.254.219",
    "35.175.63.197",
]


def update_ip_dict(ip_dict) -> dict:
    """Update IP Dict with finished jobs"""
    ip_dict_copy = deepcopy(ip_dict)
    for ip, user_id in ip_dict_copy.items():
        # No need to update an empty val
        if user_id == "":
            continue
        job = mongo_read("UserTrainingJobs", {"user_id": user_id})
        upload_status = job.get("upload_status", None)
        if upload_status == "started":
            continue

        print(f"IP {ip} with {user_id} finished with status {upload_status}")
        ip_dict_copy[ip] = ""
    return ip_dict_copy


def find_first_empty_ip(ip_dict) -> Optional[str]:
    for ip, user_id in ip_dict.items():
        if user_id == "":
            return ip
    return None


def package_model_start():
    ip_dict = {}
    for ip in ips_to_use:
        ip_dict[ip] = ""
    while True:
        all_completed_jobs = mongo_read(
            "UserTrainingJobs", {"training_status": "success"}, find_many=True
        )
        for job in all_completed_jobs:
            ip_dict = update_ip_dict(ip_dict)
            empty_ip = find_first_empty_ip(ip_dict)
            if empty_ip is None:
                continue

            upload_status = job.get("upload_status", None)
            user_id = job.get("user_id")
            if upload_status is not None and upload_status != "failure":
                continue
            ip_dict[empty_ip] = user_id
            print(f"SENDING PACKAGE REQUEST FOR {user_id} to ip {empty_ip}")
            # Send package request to next EC2 instance
            res = requests.post(f"http://{empty_ip}/upload-model/{user_id}")
            print(res.text)
        time.sleep(20)


def infer():
    while True:
        all_completed_uploads = mongo_read(
            "UserTrainingJobs", {"upload_status": "success"}, find_many=True
        )
        for job in all_completed_uploads:
            user_id = job.get("user_id")
            generation_status = job.get("generation_status", None)

            res = None
            if generation_status is None or generation_status == "failure":
                print(f"GENERATING IMAGES FOR {user_id}")
                # Send image generation query
                res = requests.post(
                    f" http://3.83.253.250/run-inference/{user_id}",
                    data=json.dumps(
                        {"endpoint_name": "stable-diffusion-mme-ep-2023-10-06-18-12-16"}
                    ),
                    headers={"content-type": "application/json"},
                )
                print(res.status_code)

            if res is None or res.status_code != 201:
                continue

            while True:
                time.sleep(10)
                curr_job = mongo_read(
                    "UserTrainingJobs",
                    {"user_id": user_id},
                )
                curr_status = curr_job.get("generation_status", None)
                print(f"{curr_status} generation status for job with user_id {user_id}")
                if curr_status == "success" or curr_status == "failure":
                    break


if __name__ == "__main__":
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--package", action="store_true")
    parser.add_argument("--infer", action="store_true")

    args = parser.parse_args()

    if args.train:
        training_thread = threading.Thread(target=run_training_job_script_loop)
        training_thread.start()
    if args.check:
        check_thread = threading.Thread(target=check_jobs)
        check_thread.start()
    if args.package:
        package_thread = threading.Thread(target=package_model_start)
        package_thread.start()
    if args.infer:
        inference_thread = threading.Thread(target=infer)
        inference_thread.start()

    while True:
        time.sleep(20)
