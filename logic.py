import threading
import uuid

from flask import Flask, Response, request
from sendblue import Sendblue

from keys import twilio_key, sendblue_key, sendblue_secret


sendblue = Sendblue(sendblue_key, sendblue_secret)


USER_ID_TO_TYPE_DICT = {1: "pizza", 2: "barbie", 3: "oppenheimer"}
USER_ID_TO_CONTEXT = {
    1: f"Another person wants to convince Pizza Man to give them a free pizza. You don't know their name.",
    2: f"Ken wants to get to know Barbie better and convince her to go on a date.",
    3: "It's 1945. Another person wants to convince Einstein to not blow up the world. You don't know their name, but you want to blow up the world because you're research paper didn't get any attention.",
}

def talk(user, new_message):
    """Talk with a specific player."""
    print("USER")
    print(user)
    print("USER NUMBER")
    print(user['number'])

    print("NEW MESSAGE")
    print(new_message)

    sendblue.send_message('+12812240743', {
        'content': 'Hello from Sendblue!',
    })
