from sendblue import Sendblue
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

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


def send_message(message, number):
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
        return resp
