import threading

from flask import Flask, Response, request
from flask_cors import CORS
from twilio.twiml.messaging_response import MessagingResponse

from auth import login
from keys import sendblue_signing_secret, is_prod, carrier
from logic import talk

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

    return "received!", 200


if __name__ == "__main__":
    app.debug = True
    if is_prod:
        context = ('/etc/letsencrypt/live/milk-be.com/fullchain.pem', '/etc/letsencrypt/live/milk-be.com/privkey.pem')
        app.run(host="0.0.0.0", port=8080, ssl_context=context)
    else:
        app.run(host="0.0.0.0", port=8080)
