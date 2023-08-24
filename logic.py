import threading
from uuid import uuid4

from flask import Flask, Response, request
from sendblue import Sendblue

from conversation.session import Session
from dbs.mongo import mongo_upsert
from messaging import send_message


def talk(user, new_message):
    """Talk with a specific player."""
    print("USER")
    print(user)
    print("USER NUMBER")
    user_num = user["number"]
    print(user_num)

    print("NEW MESSAGE")
    print(new_message)

    # If no user id, then create one before getting a session
    if user.get("user_id", None) is None:
        id = str(uuid4())
        mongo_upsert("Users", {"number": user_num}, {"user_id": id})
        user["user_id"] = id

    session_id = user.get("session_id", None)
    if session_id is None:
        curr_session = Session(user)
    else:
        curr_session = Session.from_user(user)

    next_message = curr_session.process_next_message(new_message)
    user["session_id"] = curr_session.session_id
    insertion_dict = {"number": user_num, "session_id": curr_session.session_id}
    mongo_upsert("Users", {"number": user_num}, insertion_dict)

    send_message(next_message, user["number"])
