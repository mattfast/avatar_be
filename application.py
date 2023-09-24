import asyncio
import threading
import time
from uuid import uuid4
from datetime import datetime
from random import shuffle

from flask import Flask, Response, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from twilio.twiml.messaging_response import MessagingResponse

from auth import login
from dbs.mongo import mongo_read, mongo_upsert, mongo_write
from keys import carrier, checkly_token, is_prod, lambda_token, sendblue_signing_secret
from users import get_user, get_top_users
from messaging import send_message

# import uuid


app = Flask(__name__)
CORS(app)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(
    app,
    cors_allowed_origins=[
        "http://localhost:3000",
        "https://milk-ai.com",
        "https://milk-ai.com/chat",
    ],
    async_mode="threading",
    transports=["websocket"],
)

@app.route("/generate-auth", methods=["POST"])
def generate_auth():

    # check request format
    data = request.json
    number = data.get("number", None)
    if data is None or number is None:
        return "number missing", 400

    # get and verify user
    user = get_user(number, is_number=True)
    user_id = user.get("user_id", None)
    if user is None:
        return "phone number incorrect", 401
    
    if user_id is None:
        return "user db entry faulty", 500

    # generates url search param
    search_param = str(uuid4())
    mongo_write(
        "SearchParams",
        {
            "search_param": search_param,
            "user_id": user_id,
            "created_at": datetime.now(),
        }
    )

    # sends text message w search param
    url = f"https://dopple.club/?q={search_param}"
    send_message(f"Hey! Here's your login link for dopple.club: {url}", number)
    
    return "generated search param", 200

@app.route("/verify-auth", methods=["POST"])
def verify_auth():

    # check request format
    data = request.json
    search_param = data.get("search_param", None)
    if data is None or search_param is None:
        return "search_param missing", 400

    # checks that url search param exists
    db_param = mongo_read("SearchParams", { "search_param": search_param })
    if db_param is None:
        return "search param invalid", 401
    
    user_id = db_param.get("user_id", None)
    if user_id is None:
        return "search param db entry invalid", 500

    # returns new cookie
    cookie = str(uuid4())
    mongo_write(
        "Cookies",
        {
            "search_param": search_param,
            "cookie": cookie,
            "user_id": user_id,
            "created_at": datetime.now(),
        }
    )

    return { "cookie": cookie }, 200

@app.route("/generate-feed", methods=["GET"])
def generate_feed():
    # login
    cookie = request.headers.get("auth-token")
    if cookie is None:
        return "cookie missing", 400
    
    user = get_user(cookie)
    if user is None:
        return "user invalid", 401
    
    user_id = user.get("user_id", None)
    if user_id is None:
        return "search param db entry invalid", 500

    # retrieve profiles already voted
    votes = mongo_read("Votes", { "decider_id": user_id }, find_many=True)

    # return feed w/ profiles not voted
    voted_on = [user_id]
    for v in votes:
        voted_on.append(v.get("winner_id", None))
        voted_on.append(v.get("loser_id", None))

    users_not_voted = mongo_read("Users", { "user_id": { "$nin": voted_on } }, find_many=True)
    users_list = list(users_not_voted)
    shuffle(users_list)

    return { "user_list": users_list[:24], "is_final": len(users_list) < 24 }, 200

@app.route("/post-decision", methods=["POST"])
def post_decision():

    # login
    cookie = request.headers.get("auth-token")
    if cookie is None:
        return "cookie missing", 400
    
    user = get_user(cookie)
    if user is None:
        return "user invalid", 401
    
    # validate data
    data = request.json
    winner_id = data.get("winner_id", None)
    loser_id = data.get("loser_id", None)
    if data is None or winner_id is None or loser_id is None:
        return "data invalid", 400

    # write to votes table in mongo
    # TODO: modularize into thread
    mongo_write(
        "Votes",
        {
            "voter_id": user.get("user_id", None),
            "winner_id": winner_id,
            "loser_id": loser_id,
            "created_at": datetime.now()
        }
    )

    winner = mongo_read("Users", { "user_id": winner_id })
    mongo_upsert(
        "Users",
        { "user_id": winner_id },
        { "votes": winner.get("votes", 0) + 1 }
    )

    return "posted", 200

@app.route("/send-texts", methods=["POST"])
def send_texts():

    # retrieve all users w/o text in X hrs

    return ""

@app.route("/create-user", methods=["POST"])
def create_user():

    # check request format
    data = request.json
    number = data.get("number", None)
    if data is None or number is None:
        return "number missing", 400
    
    # check for existing user
    existing_user = mongo_read("Users", { "number": number })
    if existing_user is not None:
        return "user with number already exists", 400
    
    # create new user
    user_id = str(uuid4())
    mongo_write(
        "Users",
        {
            "user_id": user_id,
            "number": number,
            "created_at": datetime.now(),
        }
    )

    # returns new cookie
    cookie = str(uuid4())
    mongo_write(
        "Cookies",
        {
            "cookie": cookie,
            "user_id": user_id,
            "created_at": datetime.now(),
        }
    )

    return { "cookie": cookie }, 200

@app.route("/update-user", methods=["POST"])
def update_user():
    # login
    cookie = request.headers.get("auth-token")
    if cookie is None:
        return "cookie missing", 400

    # check for existing user
    user = get_user(cookie)
    if user is None:
        return "user invalid", 401
    
    # insert new data
    data = request.json
    mongo_upsert("Users", { "user_id": user.get("user_id", None) }, data)

    return "success", 200

@app.route("/get-leaderboard", methods=["GET"])
def get_leaderboard():

    # login
    cookie = request.headers.get("auth-token")
    if cookie is None:
        return "cookie missing", 400
    
    user = get_user(cookie)
    if user is None:
        return "user invalid", 401

    # retrieve votes + calculate leaderboard
    leaderboard = get_top_users()

    return { leaderboard }, 200

@app.route("/profile", methods=["GET"])
def profile():

    # login
    cookie = request.headers.get("auth-token")
    if cookie is None:
        return "cookie missing", 400
    
    user = get_user(cookie)
    if user is None:
        return "user invalid", 401

    # retrieve user profile
    data = request.json
    user_id = data.get("user_id", None)
    if data is None or user_id is None:
        return "user id missing", 400

    profile = mongo_read("Users", { "user_id": user_id })
    if profile is None:
        return "profile not found", 404

    # log profile view
    # TODO: modularize into thread
    mongo_write(
        "ProfileViews",
        {
            "viewer_id": user.get("user_id", None),
            "profile_id": user_id,
            "created_at": datetime.now()
        }
    )

    return { profile }, 200


## CHECK METHODS
@app.route("/send-tiktoks-check", methods=["POST"])
def send_tiktoks_check():
    checkly_token_header = request.headers.get("checkly-token-header")

    if checkly_token_header != checkly_token:
        return "checkly token invalid", 401


    return "tiktok job completed", 200


@app.route("/bot-check", methods=["POST"])
def message_check():
    checkly_token_header = request.headers.get("checkly-token-header")

    if checkly_token_header != checkly_token:
        return "checkly token invalid", 401


    return "successfully generated", 200



if __name__ == "__main__":
    app.debug = True
    if is_prod:
        context = (
            "/etc/letsencrypt/live/milk-be.com/fullchain.pem",
            "/etc/letsencrypt/live/milk-be.com/privkey.pem",
        )
        socketio.run(
            app,
            host="0.0.0.0",
            port=8080,
            ssl_context=context,
            allow_unsafe_werkzeug=True,
        )
    else:
        socketio.run(app, host="0.0.0.0", port=8080, allow_unsafe_werkzeug=True)
