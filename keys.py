# Use this code snippet in your app.
# If you need more information about configurations
# or implementing the sample code, visit the AWS docs:
# https://aws.amazon.com/developer/language/python/

import boto3
from botocore.exceptions import ClientError
from dotenv import dotenv_values

secrets = dotenv_values(".env")
is_prod = secrets.get("IS_PROD") != "0"

# Create a Secrets Manager client
region_name = "us-east-1"
session = boto3.session.Session(
    aws_access_key_id='ACCESS_KEY',
    aws_secret_access_key='SECRET_KEY'
)
client = session.client(
    service_name='secretsmanager',
    region_name=region_name,
)

def get_secret(secret_name):

    if is_prod:
        try:
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_name
            )
        except ClientError as e:
            # For a list of exceptions thrown, see
            # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
            raise e

        # Decrypts secret using the associated KMS key.
        print(get_secret_value_response)
        secret = get_secret_value_response
        return secret
    
    return secrets.get(secret_name)

twilio_key = get_secret("TWILIO_AUTH_TOKEN")
pinecone_key = get_secret("PINECONE_API_KEY")
mongo_key = get_secret("MONGODB_PASSWORD_MATTHEW")

