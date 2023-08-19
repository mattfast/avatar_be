import threading
import uuid

from flask import Flask, Response, request
from sendblue import Sendblue

from conversation.session import Session
from dbs.mongo import mongo_upsert
from keys import sendblue_key, sendblue_secret, twilio_key

sendblue = Sendblue(sendblue_key, sendblue_secret)


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
        curr_session = Session(user)
    else:
        curr_session = Session.from_user(user)

    next_message = curr_session.process_next_message(new_message)
    user["session_id"] = curr_session.session_id
    insertion_dict = {"number": user_num, "session_id": curr_session.session_id}
    mongo_upsert("Users", {"number": user_num}, insertion_dict)

    sendblue.send_message(
        user["number"],
        {
            "content": next_message,
        },
    )
