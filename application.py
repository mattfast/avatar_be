import sys
import threading

import pinecone
import pymongo
from flask import Flask, Response, request
from flask_cors import CORS
from twilio.twiml.messaging_response import MessagingResponse

from logic import talk

app = Flask(__name__)
CORS(app)


class Increment:
    def __init__(self):
        self.id = 0

    def inc(self):
        self.id = (self.id + 1) % 3


base = Increment()
RETURN_VALS = ["not working", "lmao no shot", "hahahaha"]

# init mongodb
mongo_conection_string = "mongodb+srv://matthew:Hq8D5T7mdKQ0bztS@cluster0.4exrr9f.mongodb.net/?retryWrites=true&w=majority"
try:
    client = pymongo.MongoClient(mongo_conection_string)
except pymongo.errors.ConfigurationError:
    print(
        "An Invalid URI host error was received. Is your Atlas host name correct in your connection string?"
    )
    sys.exit(1)
else:
    print("MONGO CLIENT CREATED")
    print(client)
mongo_db = client.testDB
mongo_collection = mongo_db["testCollection"]

# init pinecone db
print("CREATING PINECONE STUFF")
pinecone.init(api_key="2c27621a-3543-459c-8e4d-c694101c8f24", environment="gcp-starter")
pinecone_index = pinecone.Index("test-index")
print("PINECONE INDEX")
print(pinecone_index)


@app.route("/bot", methods=["POST"])
def message():
    incoming_msg = request.values.get("Body", "").lower()
    user_number = request.values.get("From", "")
    resp = MessagingResponse()

    print("INCOMING MSG")
    print(incoming_msg)
    print("USER NUMBER")
    print(user_number)

    print("HERE")
    t = threading.Thread(target=talk, args=(user_number, incoming_msg))
    t.start()

    """
    ## test write to mongodb
    print("ABOUT TO TEST WRITE")
    try: 
        print("INSIDE TRY")
        result = mongo_collection.insert_one({"name": "test entry", "otherField": 0})
        print("AFTER RESULT")
        # return a friendly error if the operation fails
    except pymongo.errors.OperationFailure:
        print("An authentication error was received. Are you sure your database user is authorized to perform write operations?")
        sys.exit(1)
    else:
        inserted_id = result.inserted_id
        print(f"I inserted document with id {inserted_id}.")
        print("\n")
    """
    print("ABOUT TO UPSERT")
    upsert_response = pinecone_index.upsert(
        vectors=[("test_vec", [0.1 for i in range(1024)], {"name": "stuff"})]
    )
    print("AFTER UPSERT")
    print(upsert_response)

    return Response(str(resp), mimetype="application/xml")


if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0", port=8080)
