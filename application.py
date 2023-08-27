import asyncio
import threading

from flask import Flask, Response, request
from flask_cors import CORS
from twilio.twiml.messaging_response import MessagingResponse

from auth import login
from keys import carrier, is_prod, lambda_token, sendblue_signing_secret
from logic import talk
from tiktok.logic import delete_videos, send_videos, tag_videos, trending_videos

app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def health_check():
    return "healthy!"


@app.route("/bot", methods=["POST"])
def message():
    if carrier == "TWILIO":
        msg = request.values.get("Body", "").lower()
        number = request.values.get("From", "")
    elif carrier == "SENDBLUE":
        signing_secret = request.headers.get("sb-signing-secret")
        print(signing_secret)
        print(sendblue_signing_secret)

        if signing_secret != sendblue_signing_secret:
            return "signing secret invalid", 401

        body = request.json
        if body is None:
            return "malformed body", 400

        msg = body["content"]
        number = body["number"]
    else:
        return "invalid carrier", 500

    if number is None or number == "" or msg is None or msg == "":
        return "number or content not provided", 400

    user, is_first = login(number)
    if user is None:
        print("ERROR CREATING OR FINDING USER")
        return "unable to create or find user", 500

    print("INCOMING MSG")
    print(msg)
    print("USER NUMBER")
    print(number)

    t = threading.Thread(target=talk, args=(user, msg))
    t.start()

    return "received!", 202


@app.route("/retrieve-tiktoks", methods=["POST"])
def retrieve_tiktoks():
    lambda_token_header = request.headers.get("lambda-auth-token")

    print(lambda_token)
    print(lambda_token_header)

    if lambda_token_header != lambda_token:
        return "lambda token invalid", 401

    t = threading.Thread(target=asyncio.run, args=(trending_videos(),))
    t.start()

    return "tiktok job initiated", 202


@app.route("/delete-tiktoks", methods=["POST"])
def delete_tiktoks():
    lambda_token_header = request.headers.get("lambda-auth-token")

    print(lambda_token)
    print(lambda_token_header)

    if lambda_token_header != lambda_token:
        return "lambda token invalid", 401

    t = threading.Thread(target=asyncio.run, args=(delete_videos(),))
    t.start()

    return "tiktok job initiated", 202


@app.route("/send-tiktoks", methods=["POST"])
def send_tiktoks():
    lambda_token_header = request.headers.get("lambda-auth-token")

    print(lambda_token)
    print(lambda_token_header)

    if lambda_token_header != lambda_token:
        return "lambda token invalid", 401

    t = threading.Thread(target=asyncio.run, args=(send_videos(),))
    t.start()

    return "tiktok job initiated", 202


@app.route("/tag-tiktoks", methods=["POST"])
def tag_tiktoks():
    lambda_token_header = request.headers.get("lambda-auth-token")

    print(lambda_token)
    print(lambda_token_header)

    if lambda_token_header != lambda_token:
        return "lambda token invalid", 401

    t = threading.Thread(target=asyncio.run, args=(tag_videos(),))
    t.start()

    return "tiktok job initiated", 202


if __name__ == "__main__":
    app.debug = True
    if is_prod:
        context = (
            "/etc/letsencrypt/live/milk-be.com/fullchain.pem",
            "/etc/letsencrypt/live/milk-be.com/privkey.pem",
        )
        app.run(host="0.0.0.0", port=8080, ssl_context=context)
    else:
        app.run(host="0.0.0.0", port=8080)
