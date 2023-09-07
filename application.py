import asyncio
import threading
import time
#import uuid

from flask import Flask, Response, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from twilio.twiml.messaging_response import MessagingResponse

from auth import login
from keys import carrier, checkly_token, is_prod, lambda_token, sendblue_signing_secret
from logic import talk
from messaging import send_message
from tiktok.logic import (
    delete_videos,
    detect_video_languages,
    send_videos,
    tag_videos,
    trending_videos,
)

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins=['http://localhost:3000'], async_mode='threading', transports=['websocket'])

@socketio.on('connect', namespace="/chat")
def connect():
    print("CONNECTED")
    print("ROOM")
    print(request.sid)
    emit('connection', { 'sid': request.sid }, room=request.sid)

@socketio.on('message', namespace="/chat")
def handle_message(data):
    print('received message: ')
    print(data)

    if data is None or data["sid"] is None or data["msg"] is None or data["sid"] == "" or data["msg"] == "":
        print("DATA NOT FORMATTED CORRECTLY")
        return

    user, is_first = login(data["sid"], is_sid=True)
    if user is None:
        print("ERROR CREATING OR FINDING USER")
        return
    
    print("NEW USER")
    print(user)
    
    #t = threading.Thread(target=talk, args=(user, data["msg"]), kwargs={ 'send_ws': True, 'socket': socketio })
    #t.start()
    messages = talk(user, data["msg"], send_ws=True)
    for message in messages:
        emit('message', { 'msg': message }, room=data["sid"])
        time.sleep(0.5)

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


@app.route("/detect-language-tiktoks", methods=["POST"])
def detect_language_tiktoks():
    lambda_token_header = request.headers.get("lambda-auth-token")

    print(lambda_token)
    print(lambda_token_header)

    if lambda_token_header != lambda_token:
        return "lambda token invalid", 401

    t = threading.Thread(target=asyncio.run, args=(detect_video_languages(),))
    t.start()

    return "tiktok job initiated", 202


## CHECK METHODS
@app.route("/send-tiktoks-check", methods=["POST"])
def send_tiktoks_check():
    checkly_token_header = request.headers.get("checkly-token-header")

    if checkly_token_header != checkly_token:
        return "checkly token invalid", 401

    try:
        asyncio.run(send_videos(is_check=True))
    except Exception as e:
        return f"internal error: {e}", 500

    return "tiktok job completed", 200


@app.route("/bot-check", methods=["POST"])
def message_check():
    checkly_token_header = request.headers.get("checkly-token-header")

    if checkly_token_header != checkly_token:
        return "checkly token invalid", 401

    user, is_first = login("+11111111111")
    if user is None:
        print("ERROR CREATING OR FINDING USER")
        return "unable to create or find user", 500

    try:
        res = talk(user, "test msg", is_check=True)
    except Exception as e:
        return f"error generating message: {e}", 500

    return "successfully generated", 200


@app.route("/sendblue-check", methods=["post"])
def sendblue_check():
    checkly_token_header = request.headers.get("checkly-token-header")

    if checkly_token_header != checkly_token:
        return "checkly token invalid", 401

    try:
        send_message("test message", "+12812240743")
        send_message("test message", "+14803523815")
    except Exception as e:
        return f"error generating message: {e}", 500

    return "successfully generated", 200


if __name__ == "__main__":
    app.debug = True
    if is_prod:
        context = (
            "/etc/letsencrypt/live/milk-be.com/fullchain.pem",
            "/etc/letsencrypt/live/milk-be.com/privkey.pem",
        )
        socketio.run(app, host="0.0.0.0", port=8080, ssl_context=context, allow_unsafe_werkzeug=True)
    else:
        socketio.run(app, host="0.0.0.0", port=8080, allow_unsafe_werkzeug=True)
