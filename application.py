import asyncio
import threading
import time
from uuid import uuid4
from datetime import datetime, timedelta
from random import shuffle
from pymongo import DESCENDING

from flask import Flask, Response, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from twilio.twiml.messaging_response import MessagingResponse

from auth import login
from dbs.mongo import mongo_read, mongo_push, mongo_upsert, mongo_write, mongo_read_sort
from keys import carrier, checkly_token, is_prod, lambda_token, sendblue_signing_secret
from users import get_user, get_top_users
from messaging import send_message

text_types = [
    "viewed",
    "voted_for",
    "voted_against",
    "leaderboard",
    "total_activity"
]

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

@app.route("/")
def healthy():
    return "healthy!"

@app.route("/generate-auth", methods=["POST"])
def generate_auth():

    # check request format
    data = request.json
    number = data.get("number", None)
    if data is None or number is None:
        return "number missing", 400

    # get and verify user
    user = get_user(number, is_number=True)
    if user is None:
        return "phone number incorrect", 401

    user_id = user.get("user_id", None)
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
    send_message("Hey! Here's your login link for dopple.club:", "+1" + number)
    send_message(url, "+1" + number)
    
    return "generated search param", 200

@app.route("/verify-auth", methods=["POST"])
def verify_auth():

    # check request format
    data = request.json
    if data is None:
        return "data missing", 400

    search_param = data.get("search_param", None)
    if search_param is None:
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

@app.route("/validate-cookie", methods=["POST"])
def validate_cookie():

    # check request format
    data = request.json
    if data is None:
        return "data missing", 400
    
    cookie = data.get("cookie", None)
    if cookie is None:
        return "cookie missing", 400
    
    user = get_user(cookie)
    if user is None:
        return "user doesn't exist", 400

    gender = user.get("gender", None)
    if gender is None:
        return "user hasn't completed signup", 400
    
    return { "user_id": user.get("user_id", None) }, 200

@app.route("/get-user", methods=["GET"])
def get_user_route():

    # check request format
    cookie = request.headers.get("auth-token")
    if cookie is None:
        return "cookie missing", 400
    
    cookie = mongo_read(
        "Cookies",
        {
            "cookie": cookie,
        }
    )

    if cookie is None:
        return "cookie invalid", 400
    
    user_id = cookie.get("user_id", None)
    if user_id is None:
        return "cookie not configured properly", 500
    
    user = mongo_read(
        "Users",
        { 
            "user_id": user_id
        }
    )

    if user is None:
        return "user not found", 500
    
    return {
        "number": user.get("number", None),
        "first_name": user.get("first_name", None),
        "last_name": user.get("last_name", None),
        "gender": user.get("gender", None),
        "images_uploaded": user.get("images_uploaded", None),
        "user_id": user.get("user_id", None)
    }, 200

@app.route("/get-referral-code", methods=["GET"])
def get_referral_code():
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
    
    referral_code = mongo_read("ReferralCodes", { "user_id": user_id })

    if referral_code is None:
        referral_code = str(uuid4())
        mongo_write("ReferralCodes", {
            "user_id": user_id,
            "code": referral_code,
            "referred_users": [],
            "created_at": datetime.now()
        })
        return { "referral_code": referral_code }, 200
    
    return { "referral_code": referral_code.get("code", None) }, 200

@app.route("/confirm-referral", methods=["POST"])
def confirm_referral():
    cookie = request.headers.get("auth-token")
    if cookie is None:
        return "cookie missing", 400
    
    user = get_user(cookie)
    if user is None:
        return "user invalid", 401
    
    # check request format
    data = request.json
    if data is None:
        return "data missing", 400
    
    referral_code = data.get("referral_code", None)
    if referral_code is None:
        return "referral_code missing", 400
    
    # add users to referred users in table
    mongo_push("ReferralCodes", { "code": referral_code }, { "referred_users": user.get("user_id", None)})

    # check if other user was waiting to access feed
    ref_code_db = mongo_read("ReferralCodes", { "code": referral_code })
    other_id = ref_code_db.get("user_id", None)

    if other_id is not None:
        user = mongo_read("Users", { "user_id": other_id })

        avail_time = user.get("feed_available_at", None)
        if avail_time is not None:
            then = datetime(avail_time)
            now = datetime.now()

            # if so: 1. text them, 2. update feed_available
            if then > now:
                send_message("A friend signed up with your referral code! Your voting feed is available again:", "+1" + user.get("number", None))
                send_message("https://dopple.club/vote", "+1" + user.get("number", None))
                mongo_upsert("Users", { "user_id": other_id }, { "feed_available_at": datetime.now() })

    return "success", 200


@app.route("/generate-feed", methods=["GET"])
def generate_feed():
    # login
    cookie = request.headers.get("auth-token")
    if cookie is None:
        return "cookie missing", 400
    
    print("here1")
    
    user = get_user(cookie)
    if user is None:
        return "user invalid", 401
    
    print("here2")
    
    user_id = user.get("user_id", None)
    if user_id is None:
        return "search param db entry invalid", 500
    
    print("here3")
    
    # check if it's too soon to view feed again
    feed_available_at = user.get("feed_available_at", None)
    now = datetime.now()

    print(feed_available_at)
    print(now)
    if feed_available_at is not None and feed_available_at > now:
        return { "user_list": [], "ready_at": feed_available_at, "is_final": False }, 200
    
    print("here4")
    
    # if feed has already been generated, return it
    feed = user.get("feed", None)
    feed_index = user.get("feed_index", 0)

    print("FEED")
    print(feed)
    print("FEED INDEX")
    print(feed_index)
    if feed is not None and len(feed) > 0:
        return { "user_list": feed, "feed_index": feed_index }, 200
    
    print("here5")

    # GENERATE FEED
    # retrieve existing votes
    votes = mongo_read("Votes", { "decider_id": user_id }, find_many=True)
    voted_on = [str(user_id)]
    for v in votes:
        voted_on.append(str(v.get("winner_id", "")))
        voted_on.append(str(v.get("loser_id", "")))

    print("here6")

    # find users not voted on yet
    users_not_voted = mongo_read("Users", { "user_id": { "$nin": voted_on }, "gender": { "$exists": True } }, find_many=True)
    users_list = list(users_not_voted)
    users_list_mapped = list(map(lambda u: {
        "user_id": u.get("user_id", ""),
        "first_name": u.get("first_name", ""),
        "last_name": u.get("last_name", "")
    }, users_list))
    print(users_list_mapped)
    shuffle(users_list_mapped)

    print("here7")

    # update user with new info
    feed = users_list_mapped[:24]
    mongo_upsert("Users", { "user_id": user_id }, { "feed": feed, "feed_index": 0 })

    print("here8")

    return { "user_list": feed, "feed_index": 0 }, 200

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
    mongo_write(
        "Votes",
        {
            "voter_id": user.get("user_id", None),
            "winner_id": winner_id,
            "loser_id": loser_id,
            "created_at": datetime.now()
        }
    )

    # update winners' table
    winner = mongo_read("Users", { "user_id": winner_id })
    mongo_upsert(
        "Users",
        { "user_id": winner_id },
        { "votes": winner.get("votes", 0) + 1 }
    )

    # update feed_index (and feed_available_at + notified_about_feed if necessary)
    feed_index = user.get("feed_index", 0)
    feed_index += 2
    if feed_index >= 23:
        now = datetime.now()
        future_time = now + timedelta(minutes=40)
        mongo_upsert("Users", { "user_id": user.get("user_id", "") }, { "feed": [], "notified_about_feed": False, "feed_available_at": future_time })
    else:
        mongo_upsert("Users", { "user_id": user.get("user_id", "") }, { "feed_index": feed_index })

    return "posted", 200

@app.route("/send-text-blast", methods=["POST"])
def send_text_blast():
    lambda_token_header = request.headers.get("lambda-token-header")

    if lambda_token_header != lambda_token:
        return "lambda token invalid", 401

    users = mongo_read("Users", {}, find_many=True)

    if users is None:
        return "users not found", 500

    for u in users:
        if u is None:
            continue
        num = u.get("number", None)
        if num is None:
            continue

        send_message("🚨ALERT🚨 Your dopple is ready to view. Look here to see yours and your friends':", "+1" + num)
        send_message("https://dopple.club/vote", "+1" + num)

    return "text blast sent", 200

@app.route("/send-feed-texts", methods=["POST"])
def send_feed_texts():
    lambda_token_header = request.headers.get("lambda-token-header")

    if lambda_token_header != lambda_token:
        return "lambda token invalid", 401
    
    users = mongo_read("Users", {}, find_many=True)

    if users is None:
        return "users not found", 500

    now = datetime.now()
    for u in users:
        if u is None:
            continue
        feed_available_at = u.get("feed_available_at", None)
        notified_about_feed = u.get("notified_about_feed", None)
        if feed_available_at is not None and not notified_about_feed:
            if feed_available_at < now:
                send_message("Your feed is ready again! Check out some more profiles:", "+1" + u.get("number", ""))
                send_message("https://dopple.club/vote", "+1" + u.get("number", ""))
                mongo_upsert("Users", { "user_id": u.get("user_id", None) }, { "notified_about_feed": True })

    return "success", 200

"""@app.route("/send-digest-texts", methods=["POST"])
def send_update_texts():
    lambda_token_header = request.headers.get("lambda-token-header")

    if lambda_token_header != lambda_token:
        return "lambda token invalid", 401
    
    users = mongo_read("Users", {}, find_many=True)

    if users is None:
        return "users not found", 500
    
    for u in users:
        if u is None:
            continue
        u_id = u.get("user_id", None)
        if u_id is None:
            continue

        texts = mongo_read_sort("TextsSent", { "user_id": u_id }, { "created_at": -1 }, limit=10)
        now = datetime.now() - 
        if texts.length == 0 or datetime.datetime(texts[0].get("created_at", None)):

            


    return ""
"""

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

    return { "cookie": cookie, "user_id": user_id }, 200

@app.route("/update-user", methods=["POST"])
def update_user():
    # login
    cookie = request.headers.get("auth-token")
    if cookie is None:
        return "cookie missing", 400
    
    print(cookie)

    # check for existing user
    user = get_user(cookie)
    if user is None:
        return "user invalid", 401
    
    # insert new data
    data = request.json
    mongo_upsert("Users", { "user_id": user.get("user_id", None) }, data)

    # send text if they just completed signup flow
    gender = data.get("gender", None)
    number = user.get("number", None)
    if gender is not None and number is not None:
        send_message("Thanks for signing up for dopple.club!", "+1" + number)
        send_message("Reply to this message with \"YES\" to make your experience better :)", "+1" + number)

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
    top_users = get_top_users()
    print("TOP USERS")
    print(top_users)
    if top_users is None:
        return { "leaderboard": [] }, 200
    leaderboard_list = list(top_users)
    print("LEADERBOARD LIST")
    print(leaderboard_list)
    leaderboard_map_list = list(map(lambda l: {
        "user_id": l["user_id"],
        "first_name": l["first_name"],
        "last_name": l["last_name"],
    }, leaderboard_list))

    return { "leaderboard": leaderboard_map_list }, 200

@app.route("/profile/<user_id>", methods=["GET"])
def profile(user_id):

    # login
    cookie = request.headers.get("auth-token")
    if cookie is None:
        return "cookie missing", 400
    
    user = get_user(cookie)
    if user is None:
        return "user invalid", 401

    # retrieve user profile
    #data = request.json
    #user_id = data.get("user_id", None)
    if user_id is None:
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

    users = list(get_top_users())
    pos = 0
    for i in range(len(users)):
        if users[i]["user_id"] == user_id:
            pos = i + 1
            break

    return {
        "themes": profile.get("image_config", None),
        "first_name": profile.get("first_name", None),
        "last_name": profile.get("last_name", None),
        "position": pos
    }, 200


## CHECK METHODS
@app.route("/send-tiktoks-check", methods=["POST"])
def send_tiktoks_check():
    checkly_token_header = request.headers.get("checkly-token-header")

    if checkly_token_header != checkly_token:
        return "checkly token invalid", 401


    return "tiktok job completed", 200


@app.route("/test-message", methods=["GET"])
def test_message():
    send_message("hi!", "+12812240743")
    return "done", 200




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
