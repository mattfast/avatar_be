import threading
import time
from uuid import uuid4

from flask import Flask, Response, request
from sendblue import Sendblue

from conversation.session import Session
from dbs.mongo import mongo_read, mongo_upsert

MAX_WAIT_TIME_SECS = 5


def talk(user, new_message, is_check=False):
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

    curr_session = Session.from_user(user)

    user["session_id"] = curr_session.session_id
    insertion_dict = {"number": user_num, "session_id": curr_session.session_id}
    mongo_upsert("Users", {"number": user_num}, insertion_dict)

    start_time = time.time()
    next_messages = curr_session.process_next_message(new_message)
    end_time = time.time()
    time_elapsed = end_time - start_time

    if time_elapsed < MAX_WAIT_TIME_SECS:
        sleep_time = MAX_WAIT_TIME_SECS - time_elapsed
        time.sleep(sleep_time)
    last_message_id = curr_session.user_messages[-1].message_id

    messages = mongo_read(
        "Messages", {"session_id": curr_session.session_id}, find_many=True
    )
    last_message = None

    # Get Newest Message
    for message in messages.sort("created_time", -1):
        last_message = message
        break

    print(last_message_id)
    print(last_message)

    if (
        last_message is None
        or last_message.get("message_id", None) == last_message_id
        and not is_check
    ):
        for next_message in next_messages:
            next_message.send(user["number"])
            time.sleep(0.5)
        curr_session.update_on_send(next_messages)
