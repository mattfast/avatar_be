import threading
import time
from uuid import uuid4

from flask import Flask, Response, request
from sendblue import Sendblue

from conversation.session import Session
from dbs.mongo import mongo_read, mongo_upsert

# from flask_socketio import emit

# from application import socketio

MAX_WAIT_TIME_SECS = 5


def talk(user, new_message, is_check=False, send_ws=False):
    """Talk with a specific player."""
    print("USER")
    print(user)
    print("USER NUMBER")
    user_num = user["number"]
    user_sid = user.get("sid", None)
    print(user_num)

    print("NEW MESSAGE")
    print(new_message)

    # If no user id, then create one before getting a session
    if user.get("user_id", None) is None:
        id = str(uuid4())
        if send_ws:
            mongo_upsert("Users", {"sid": user_sid}, {"user_id": id})
        else:
            mongo_upsert("Users", {"number": user_num}, {"user_id": id})
        user["user_id"] = id

    curr_session = Session.from_user(user)

    user["session_id"] = curr_session.session_id
    if send_ws:
        insertion_dict = {"sid": user_sid, "session_id": curr_session.session_id}
        mongo_upsert("Users", {"sid": user_sid}, insertion_dict)
    else:
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
        messages = []
        is_first = True
        for next_message in next_messages:
            if send_ws:
                messages.append(next_message.content)
                next_message.log_to_mongo()

                ## detect if first conversation is over
                if next_message.metadata.get("is_first_conversation", True) == False:
                    is_first = False
            else:
                next_message.send(user["number"])
                time.sleep(0.5)
        curr_session.update_on_send(next_messages)

        return messages, is_first

    return [], True
