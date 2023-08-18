import threading
import uuid

from flask import Flask, Response, request
from sendblue import Sendblue

from conversation.session import Session
from dbs.mongo import mongo_upsert
from keys import sendblue_key, sendblue_secret, twilio_key

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
    user_num = user["number"]
    print(user_num)

    print("NEW MESSAGE")
    print(new_message)

    session_id = user.get("session_id", None)
    if session_id is None:
        curr_session = Session(user_num)
    else:
        curr_session = Session.from_user(user)

    next_message = curr_session.process_next_message(new_message)
    user["session_id"] = curr_session.session_id
    insertion_dict = {
        "number": user_num,
        "session_id": curr_session.session_id
    }
    mongo_upsert("Users", {"number": user_num}, insertion_dict)

    sendblue.send_message(
        user["number"],
        {
            "content": next_message,
        },
    )
