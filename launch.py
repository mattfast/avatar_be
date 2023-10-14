import argparse
import subprocess
from constants import PATH_PREFIX
from train_model import launch_modal_training_command

parser = argparse.ArgumentParser()

urls = ['https://dopple-selfies.s3.amazonaws.com/selfie-0-20c40a9c-4988-4ab7-a7d3-5af51348bf13.jpg?AWSAccessKeyId=AKIAV2MBTO4PKRWFUZZF&Signature=XPAr%2F1RrK%2FnXewt11Zg9ivUXVXM%3D&Expires=1697309818',
 'https://dopple-selfies.s3.amazonaws.com/selfie-1-20c40a9c-4988-4ab7-a7d3-5af51348bf13.jpg?AWSAccessKeyId=AKIAV2MBTO4PKRWFUZZF&Signature=xwAAchP%2FuKuQao0Uobgpd9QtzGU%3D&Expires=1697309818',
 'https://dopple-selfies.s3.amazonaws.com/selfie-2-20c40a9c-4988-4ab7-a7d3-5af51348bf13.jpg?AWSAccessKeyId=AKIAV2MBTO4PKRWFUZZF&Signature=YbxO71KqwoMcbuYkT%2F7D%2F3Fm7OU%3D&Expires=1697309818',
 'https://dopple-selfies.s3.amazonaws.com/selfie-3-20c40a9c-4988-4ab7-a7d3-5af51348bf13.jpg?AWSAccessKeyId=AKIAV2MBTO4PKRWFUZZF&Signature=DYKAo1j5lFAE2qKva3A25E3V5Is%3D&Expires=1697309818',
 'https://dopple-selfies.s3.amazonaws.com/selfie-4-20c40a9c-4988-4ab7-a7d3-5af51348bf13.jpg?AWSAccessKeyId=AKIAV2MBTO4PKRWFUZZF&Signature=uVSwP0XSHiCMWm7ULBC1c97v0k4%3D&Expires=1697309818']


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


def launch_command(urls: list[str], user_id, upload_only: bool = False):
    combined_urls = "\n".join(urls)
    upload_only_str = "true" if upload_only else "false"

    prefix = PATH_PREFIX

    cmd = [
        "modal",
        "run",
        f"{prefix}modal_dreambooth.py",
        f"--user={user_id}",
        f"--urls={combined_urls}",
        f"--upload-only={upload_only_str}",
    ]

    try:
        _exec_subprocess(cmd)
    except:
        # Call failure
        print("ERROR")


if __name__ == "__main__":
    launch_command(urls, "AKASH_USER")

# Test this on EC2 by installing new dependencies
# test this end to end (with s3 uploading)
# add failure catches
# change rest of script to accomodate this flow


######## .... installing requirements ########
# sudo apt install awscli
# TOKEN=$(aws --region us-east-1 secretsmanager get-secret-value --secret-id arn:aws:secretsmanager:us-east-1:400240637726:secret:ModalAPISecret-3ywzh1 --query SecretString --output text | cut -d: -f2 | tr -d \"})
# modal token set --token-id ak-0gdVZa8Bo3SuuqTnlpje5S --token-secret TOKEN
