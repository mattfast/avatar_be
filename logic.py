import threading
import uuid

from flask import Flask, Response, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

from keys import twilio_key

USER_ID_TO_TYPE_DICT = {1: "pizza", 2: "barbie", 3: "oppenheimer"}
USER_ID_TO_CONTEXT = {
    1: f"Another person wants to convince Pizza Man to give them a free pizza. You don't know their name.",
    2: f"Ken wants to get to know Barbie better and convince her to go on a date.",
    3: "It's 1945. Another person wants to convince Einstein to not blow up the world. You don't know their name, but you want to blow up the world because you're research paper didn't get any attention.",
}

account_sid = "ACfe453c3ef8654f6859d7aab0e23cd10f"
twilio_number = "+14066312474"
client = Client(account_sid, twilio_key)


def talk(user_number, new_message):
    """Talk with a specific player."""
    print("USER NUMBER")
    print(user_number)

    print("NEW MESSAGE")
    print(new_message)

    client.messages.create(
        body="Hi",
        from_=twilio_number,
        to=user_number,
    )
