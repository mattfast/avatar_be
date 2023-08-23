import threading

from flask import Flask, Response, request
from flask_cors import CORS
from twilio.twiml.messaging_response import MessagingResponse

from auth import login
from keys import is_prod, sendblue_signing_secret
from logic import talk

app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def health_check():
    return "healthy!"


@app.route("/bot", methods=["POST"])
def message():
    signing_secret = request.headers.get("sb-signing-secret")

    print(signing_secret)
    print(sendblue_signing_secret)

    if signing_secret != sendblue_signing_secret:
        return "signing secret invalid", 401

    body = request.json
    print(body)

    if body is None or body["number"] is None or body["content"] is None:
        return "malformed body", 400

    user, is_first = login(body["number"])
    if user is None:
        print("ERROR CREATING OR FINDING USER")
        return "unable to create or find user", 500

    print("INCOMING MSG")
    print(body["content"])
    print("USER NUMBER")
    print(body["number"])

    t = threading.Thread(target=talk, args=(user, body["content"]))
    t.start()

    return "received!", 200


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
