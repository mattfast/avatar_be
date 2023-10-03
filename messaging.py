import datetime
from enum import Enum, auto

from sendblue import Sendblue
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

from dbs.mongo import mongo_write
from keys import (
    carrier,
    sendblue_key,
    sendblue_secret,
    twilio_account_sid,
    twilio_key,
    twilio_number,
)

client = Client(twilio_account_sid, twilio_key)
sendblue = Sendblue(sendblue_key, sendblue_secret)


class TextType(Enum):
    UNLOCK_FEED_AUTO = "unlock_feed_auto"
    UNLOCK_FEED_MANUAL = "unlock_feed_manual"
    ALERT = "alert"
    VIEWED = "viewed"
    VOTED_FOR = "voted_for"
    VOTED_AGAINST = "voted_against"
    LEADERBOARD = "leaderboard"


def send_message(
    message, number, message_type=None, user_id=None, text_id=None, log=False
):
    resp = None
    try:
        if carrier == "TWILIO":
            print(message)
            print(number)
            print(twilio_number)
            print(twilio_account_sid)
            print(twilio_key)
            resp = client.messages.create(
                body=message,
                from_=twilio_number,
                to=number,
            )
        elif carrier == "SENDBLUE":
            resp = sendblue.send_message(
                number,
                {
                    "content": message,
                },
            )
        else:
            print("CARRIER NOT RECOGNIZED")
    except:
        print("ERROR SENDING MESSAGE")
        print(resp)
        return resp
    else:
        print("successfully sent message")
        print(resp)

        # log message to mongo
        if log:
            now = datetime.now()
            mongo_write(
                "Texts",
                {
                    "text_id": text_id,
                    "message": message,
                    "created_at": now,
                    "opened": False,
                    "type": message_type,
                    "user_id": user_id,
                },
            )

        return resp
