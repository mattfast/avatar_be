import subprocess

urls = ['https://dopple-selfies.s3.amazonaws.com/selfie-0-20c40a9c-4988-4ab7-a7d3-5af51348bf13.jpg?AWSAccessKeyId=AKIAV2MBTO4PKRWFUZZF&Signature=x6EXC1avNPZ8wf%2B0ezLEiOjNY%2FE%3D&Expires=1697221184',
 'https://dopple-selfies.s3.amazonaws.com/selfie-1-20c40a9c-4988-4ab7-a7d3-5af51348bf13.jpg?AWSAccessKeyId=AKIAV2MBTO4PKRWFUZZF&Signature=UZ67IDEcr13sIf72RCQzwgQv6og%3D&Expires=1697221184',
 'https://dopple-selfies.s3.amazonaws.com/selfie-2-20c40a9c-4988-4ab7-a7d3-5af51348bf13.jpg?AWSAccessKeyId=AKIAV2MBTO4PKRWFUZZF&Signature=PitpR%2F6a%2Bfxe3kxIKlfXz7flfcQ%3D&Expires=1697221184',
 'https://dopple-selfies.s3.amazonaws.com/selfie-3-20c40a9c-4988-4ab7-a7d3-5af51348bf13.jpg?AWSAccessKeyId=AKIAV2MBTO4PKRWFUZZF&Signature=buApOHKTLFLBLlp%2FKdnrWILodrg%3D&Expires=1697221184',
 'https://dopple-selfies.s3.amazonaws.com/selfie-4-20c40a9c-4988-4ab7-a7d3-5af51348bf13.jpg?AWSAccessKeyId=AKIAV2MBTO4PKRWFUZZF&Signature=D8ZWhnjSPwgjgaEY4fe8Z%2FqvMBU%3D&Expires=1697221184']
prefix = "weird_prefix"


def _exec_subprocess(cmd: list[str]):
    """Executes subprocess and prints log to terminal while subprocess is running."""
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    # with process.stdout as pipe:
    #     for line in iter(pipe.readline, b""):
    #         line_str = line.decode()
    #         print(f"{line_str}", end="")
    #
    # if exitcode := process.wait() != 0:
    #     raise subprocess.CalledProcessError(exitcode, "\n".join(cmd))


def launch_command(urls: list[str], user_id):
    combined_urls = "\n".join(urls)

    prefix = "/home/ubuntu/avatar_be/"

    cmd = [
        "modal",
        "run",
        f"{prefix}modal_dreambooth.py",
        f"--user={user_id}",
        f"--urls={combined_urls}"
    ]

    try:
        _exec_subprocess(cmd)
    except:
        # Call failure
        print("ERROR")


if __name__ == "__main__":
    launch_command(urls, "AKASH_FAKE_USER")

# Test this on EC2 by installing new dependencies
# test this end to end (with s3 uploading)
# add failure catches
# change rest of script to accomodate this flow


######## .... installing requirements ########
# sudo apt install awscli
# TOKEN=$(aws --region us-east-1 secretsmanager get-secret-value --secret-id arn:aws:secretsmanager:us-east-1:400240637726:secret:ModalAPISecret-3ywzh1 --query SecretString --output text | cut -d: -f2 | tr -d \"})
# modal token set --token-id ak-0gdVZa8Bo3SuuqTnlpje5S --token-secret TOKEN