
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from sendblue import Sendblue

from keys import twilio_account_sid, twilio_key, twilio_number, sendblue_key, sendblue_secret, carrier

client = Client(twilio_account_sid, twilio_key)
sendblue = Sendblue(sendblue_key, sendblue_secret)

def send_message(message, number):
    try:
        if carrier == "TWILIO":
            print(message)
            print(number)
            print(twilio_number)
            print(twilio_account_sid)
            print(twilio_key)
            client.messages.create(
                body=message,
                from_=twilio_number,
                to=number,
            )
        elif carrier == "SENDBLUE":
            sendblue.send_message(
                number,
                {
                    "content": message,
                },
            )
        else:
            print("CARRIER NOT RECOGNIZED")
    except:
        print("ERROR SENDING MESSAGE")
    else:
        print("successfully sent message")