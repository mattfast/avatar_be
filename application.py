import threading

from flask import Flask, Response, request
from flask_cors import CORS
from twilio.twiml.messaging_response import MessagingResponse

from logic import talk
from db import pinecone_index
from auth import login

app = Flask(__name__)
CORS(app)

class Increment:
    def __init__(self):
        self.id = 0

    def inc(self):
        self.id = (self.id + 1) % 3


base = Increment()
RETURN_VALS = ["not working", "lmao no shot", "hahahaha"]

@app.route("/", methods=["GET"])
def health_check():
    return 'healthy!'

@app.route("/bot", methods=["POST"])
def message():
    incoming_msg = request.values.get("Body", "").lower()
    user_number = request.values.get("From", "")
    resp = MessagingResponse()

    user, is_first = login(user_number)
    if user is None:
        print("ERROR CREATING OR FINDING USER")
        return Response(str(resp), mimetype="application/xml")

    print("INCOMING MSG")
    print(incoming_msg)
    print("USER NUMBER")
    print(user_number)

    t = threading.Thread(target=talk, args=(user, incoming_msg))
    t.start()

    print("ABOUT TO UPSERT")
    upsert_response = pinecone_index.upsert(
        vectors=[("test_vec", [0.1 for i in range(1024)], {"name": "stuff"})]
    )
    print("AFTER UPSERT")
    print(upsert_response)

    return Response(str(resp), mimetype="application/xml")


if __name__ == "__main__":
    app.debug = True
    context = ('cert.crt', 'cert.key')
    app.run(host="0.0.0.0", port=8080, ssl_context=context)

