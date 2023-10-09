import asyncio
import threading
import time
from datetime import datetime, timedelta
from random import shuffle
from uuid import uuid4

from flask import Flask, Response, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from pymongo import DESCENDING
from twilio.twiml.messaging_response import MessagingResponse

from auth import login
from dbs.mongo import mongo_push, mongo_read, mongo_read_sort, mongo_upsert, mongo_write
from keys import carrier, checkly_token, is_prod, lambda_token, sendblue_signing_secret
from messaging import TextType, send_message
from package_model import package_model
from run_inference import generate_all_images
from scripts.main import run_training_job_script
from train_model import check_job_status, post_request
from users import get_top_users, get_user

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
        },
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
    db_param = mongo_read("SearchParams", {"search_param": search_param})
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
        },
    )

    return {"cookie": cookie}, 200


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

    images_generated = user.get("images_generated", None)
    if images_generated is None:
        return "user hasn't completed signup", 400

    return {"user_id": user.get("user_id", None)}, 200


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
        },
    )

    if cookie is None:
        return "cookie invalid", 400

    user_id = cookie.get("user_id", None)
    if user_id is None:
        return "cookie not configured properly", 500

    user = mongo_read("Users", {"user_id": user_id})

    if user is None:
        return "user not found", 500

    return {
        "number": user.get("number", None),
        "first_name": user.get("first_name", None),
        "last_name": user.get("last_name", None),
        "gender": user.get("gender", None),
        "images_generated": user.get("images_generated", None),
        "images_uploaded": user.get("images_uploaded", None),
        "user_id": user.get("user_id", None),
        "primary_image": user.get("primary_image", 0),
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

    referral_code = mongo_read("ReferralCodes", {"user_id": user_id})

    if referral_code is None:
        referral_code = str(uuid4())
        mongo_write(
            "ReferralCodes",
            {
                "user_id": user_id,
                "code": referral_code,
                "referred_users": [],
                "created_at": datetime.now(),
            },
        )
        return {"referral_code": referral_code}, 200

    return {"referral_code": referral_code.get("code", None)}, 200


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
    mongo_push(
        "ReferralCodes",
        {"code": referral_code},
        {"referred_users": user.get("user_id", None)},
    )

    # check if other user was waiting to access feed
    ref_code_db = mongo_read("ReferralCodes", {"code": referral_code})
    other_id = ref_code_db.get("user_id", None)

    if other_id is not None:
        user = mongo_read("Users", {"user_id": other_id})

        avail_time = user.get("feed_available_at", None)
        if avail_time is not None:
            then = datetime(avail_time)
            now = datetime.now()

            # if so: 1. text them, 2. update feed_available
            if then > now:
                text_id = str(uuid4())
                send_message(
                    "A friend signed up with your referral code! Your voting feed is available again:",
                    "+1" + user.get("number", None),
                )
                send_message(
                    f"https://dopple.club/vote?t={text_id}",
                    "+1" + user.get("number", ""),
                    message_type=TextType.UNLOCK_FEED_MANUAL,
                    user_id=user.get("user_id", None),
                    text_id=text_id,
                    log=True,
                )
                mongo_upsert(
                    "Users",
                    {"user_id": other_id},
                    {"feed_available_at": datetime.now()},
                )

    return "success", 200


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

    # check if it's too soon to view feed again
    feed_available_at = user.get("feed_available_at", None)
    now = datetime.now()

    if feed_available_at is not None and feed_available_at > now:
        return {"user_list": [], "ready_at": feed_available_at, "is_final": False}, 200

    # if feed has already been generated, return it
    feed = user.get("feed", None)
    feed_index = user.get("feed_index", 0)

    if feed is not None and len(feed) > 0:
        return {"user_list": feed, "feed_index": feed_index}, 200

    # GENERATE FEED
    # retrieve existing votes
    votes = mongo_read("Votes", {"decider_id": user_id}, find_many=True)
    voted_on = [str(user_id)]
    for v in votes:
        voted_on.append(str(v.get("winner_id", "")))
        voted_on.append(str(v.get("loser_id", "")))

    print("here6")

    # find users not voted on yet
    users_not_voted = mongo_read(
        "Users",
        {"user_id": {"$nin": voted_on}, "images_generated": True},
        find_many=True,
    )
    users_list = list(users_not_voted)
    users_list_mapped = list(
        map(
            lambda u: {
                "user_id": u.get("user_id", ""),
                "first_name": u.get("first_name", ""),
                "last_name": u.get("last_name", ""),
                "primary_image": u.get("primary_image", 0),
            },
            users_list,
        )
    )
    print(users_list_mapped)
    shuffle(users_list_mapped)

    print("here7")

    # update user with new info
    feed = users_list_mapped[:24]
    mongo_upsert("Users", {"user_id": user_id}, {"feed": feed, "feed_index": 0})

    print("here8")

    return {"user_list": feed, "feed_index": 0}, 200


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
            "created_at": datetime.now(),
        },
    )

    # update winners' table
    winner = mongo_read("Users", {"user_id": winner_id})
    mongo_upsert("Users", {"user_id": winner_id}, {"votes": winner.get("votes", 0) + 1})

    # update feed_index (and feed_available_at + notified_about_feed if necessary)
    feed_index = user.get("feed_index", 0)
    feed_index += 2
    if feed_index >= 23:
        now = datetime.now()
        future_time = now + timedelta(minutes=40)
        mongo_upsert(
            "Users",
            {"user_id": user.get("user_id", "")},
            {
                "feed": [],
                "notified_about_feed": False,
                "feed_available_at": future_time,
            },
        )
    else:
        mongo_upsert(
            "Users", {"user_id": user.get("user_id", "")}, {"feed_index": feed_index}
        )

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

        text_id = str(uuid4())
        user_id = u.get("user_id", None)
        send_message(
            "🚨ALERT🚨 Your dopple is ready to view. Look here to see your options:",
            "+1" + num,
        )
        send_message(
            f"https://dopple.club/profile/${user_id}?t={text_id}",
            "+1" + u.get("number", ""),
            message_type=TextType.ALERT,
            user_id=user_id,
            text_id=text_id,
            log=True,
        )

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
                text_id = str(uuid4())
                send_message(
                    "Your feed is ready again! Check out some more profiles:",
                    "+1" + u.get("number", ""),
                )
                send_message(
                    f"https://dopple.club/vote?t={text_id}",
                    "+1" + u.get("number", ""),
                    message_type=TextType.UNLOCK_FEED_AUTO,
                    user_id=u.get("user_id", None),
                    text_id=text_id,
                    log=True,
                )
                mongo_upsert(
                    "Users",
                    {"user_id": u.get("user_id", None)},
                    {"notified_about_feed": True},
                )

    return "success", 200


@app.route("/send-digest-texts", methods=["POST"])
def send_update_texts():
    lambda_token_header = request.headers.get("lambda-token-header")

    if lambda_token_header != lambda_token:
        return "lambda token invalid", 401

    users = mongo_read("Users", {}, find_many=True)

    if users is None:
        return "users not found", 500

    data = request.json
    if data is None:
        return "no data", 400

    text_type = data.get("text_type", None)
    if text_type is None:
        return "no text_type", 400

    if text_type == "viewed":
        views = mongo_read_sort(
            "ProfileViews", {}, [("profile_id", DESCENDING)], limit=None
        )
        view_count = {}
        for view in views:
            profile_id = view["profile_id"]
            if profile_id in view_count:
                view_count[profile_id] += 1
            else:
                view_count[profile_id] = 1

        for profile_id in view_count.keys():
            count = view_count[profile_id]
            if count > 1:
                user = mongo_read("Users", {"user_id": profile_id})
                if user is None:
                    continue
                number = user.get("number", None)
                text_id = str(uuid4())
                send_message(
                    f"{count} people have viewed your profile today 👀", "+1" + number
                )
                send_message(f"Join the action:", "+1" + number)
                send_message(
                    f"https://dopple.club/vote?t={text_id}",
                    "+1" + number,
                    message_type=TextType.VIEWED,
                    user_id=profile_id,
                    text_id=text_id,
                    log=True,
                )

    elif text_type == "voted_for":
        votes = mongo_read_sort("Votes", {}, [("winner_id", DESCENDING)], limit=None)
        vote_count = {}
        for vote in votes:
            winner_id = vote["winner_id"]
            if winner_id in vote_count:
                vote_count[winner_id] += 1
            else:
                vote_count[winner_id] = 1

        for winner_id in vote_count.keys():
            count = vote_count[winner_id]
            if count > 1:
                user = mongo_read("Users", {"user_id": winner_id})
                if user is None:
                    continue
                number = user.get("number", None)
                text_id = str(uuid4())
                send_message(
                    f"{count} people have voted for you today 🎉", "+1" + number
                )
                send_message(f"Open to see who:", "+1" + number)
                send_message(
                    f"https://dopple.club/vote?t={text_id}",
                    "+1" + number,
                    message_type=TextType.VOTED_FOR,
                    user_id=winner_id,
                    text_id=text_id,
                    log=True,
                )

    elif text_type == "voted_against":
        votes = mongo_read_sort("Votes", {}, [("loser_id", DESCENDING)], limit=None)
        vote_count = {}
        for vote in votes:
            loser_id = vote["loser_id"]
            if loser_id in vote_count:
                vote_count[loser_id] += 1
            else:
                vote_count[loser_id] = 1

        for loser_id in vote_count.keys():
            count = vote_count[loser_id]
            if count > 1:
                user = mongo_read("Users", {"user_id": loser_id})
                if user is None:
                    continue
                number = user.get("number", None)
                text_id = str(uuid4())
                send_message(
                    f"{count} people have voted against you today 😬", "+1" + number
                )
                send_message(f"Open to see who:", "+1" + number)
                send_message(
                    f"https://dopple.club/vote?t={text_id}",
                    "+1" + number,
                    message_type=TextType.VOTED_AGAINST,
                    user_id=loser_id,
                    text_id=text_id,
                    log=True,
                )

    elif text_type == "leaderboard":
        leaderboard = get_top_users()
        for i in range(len(leaderboard)):
            number = leaderboard[i].get("number", None)
            user_id = leaderboard[i].get("user_id", None)
            text_id = str(uuid4())
            send_message(
                f"You're currently sitting at #{i+1} in the leaderboard 😏",
                "+1" + number,
            )
            send_message(f"Check out where your friends are:", "+1" + number)
            send_message(
                f"https://dopple.club/leaderboard?t={text_id}",
                "+1" + number,
                message_type=TextType.LEADERBOARD,
                user_id=user_id,
                text_id=text_id,
                log=True,
            )

    return "texts sent!", 200


@app.route("/mark-text-opened", methods=["POST"])
def mark_text_opened():

    cookie = request.headers.get("auth-token")
    if cookie is None:
        return "cookie missing", 400

    data = request.json
    if data is None:
        return "data missing", 400

    text_id = data.get("text_id", None)
    if text_id is None:
        return "text_id missing", 400

    mongo_upsert("Texts", {"text_id": text_id}, {"opened": True})

    return "updated", 200


@app.route("/create-user", methods=["POST"])
def create_user():

    # check request format
    data = request.json
    if data is None:
        return "data missing", 400

    number = data.get("number", None)
    if number is None:
        return "number missing", 400

    # check for existing user
    existing_user = mongo_read("Users", {"number": number})
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
        },
    )

    # returns new cookie
    cookie = str(uuid4())
    mongo_write(
        "Cookies",
        {
            "cookie": cookie,
            "user_id": user_id,
            "created_at": datetime.now(),
        },
    )

    return {"cookie": cookie, "user_id": user_id}, 200


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
    mongo_upsert("Users", {"user_id": user.get("user_id", None)}, data)

    # send text if they just completed signup flow
    gender = data.get("gender", None)
    number = user.get("number", None)
    if gender is not None and number is not None:
        send_message("Thanks for signing up for dopple.club!", "+1" + number)
        send_message(
            'Reply to this message with "YES" to make your experience better :)',
            "+1" + number,
        )

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
        return {"leaderboard": []}, 200
    leaderboard_list = list(top_users)
    print("LEADERBOARD LIST")
    print(leaderboard_list)
    leaderboard_map_list = list(
        map(
            lambda l: {
                "user_id": l["user_id"],
                "first_name": l["first_name"],
                "last_name": l["last_name"],
                "primary_image": l.get("primary_image", 0),
            },
            leaderboard_list,
        )
    )

    return {"leaderboard": leaderboard_map_list}, 200


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
    # data = request.json
    # user_id = data.get("user_id", None)
    if user_id is None:
        return "user id missing", 400

    profile = mongo_read("Users", {"user_id": user_id})
    if profile is None:
        return "profile not found", 404

    # log profile view
    # TODO: modularize into thread
    mongo_write(
        "ProfileViews",
        {
            "viewer_id": user.get("user_id", None),
            "profile_id": user_id,
            "created_at": datetime.now(),
        },
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
        "primary_image": profile.get("primary_image", 0),
        "position": pos,
    }, 200


@app.route("/set-primary-image", methods=["POST"])
def set_primary_image():

    cookie = request.headers.get("auth-token")
    if cookie is None:
        return "cookie missing", 400

    user = get_user(cookie)
    if user is None:
        return "user invalid", 401

    data = request.json
    if data is None:
        return "no data", 400

    primary_image = data.get("primary_image", None)
    if primary_image is None:
        return "no primary_image", 400

    if primary_image < 10 and primary_image >= 0:
        mongo_upsert(
            "Users",
            {"user_id": user.get("user_id", None)},
            {"primary_image": primary_image},
        )

    return "done", 200


@app.route("/train-user-models", methods=["POST"])
def train_user_models():
    training_thread = threading.Thread(target=run_training_job_script)
    training_thread.start()
    return "training script started", 201


# Upload User Model to s3
@app.route("/upload-models", methods=["POST"])
def upload_models():
    data = request.json
    ip = data.get("ip", None)
    if ip is None:
        return "no ip", 400

    current_jobs = mongo_read(
        "UserTrainingJobs",
        {"upload_ip": ip, "upload_status": "started"},
        find_many=True,
    )

    if current_jobs is not None and len(list(current_jobs)) >= 2:
        return "too many jobs", 503

    new_job = mongo_read(
        "UserTrainingJobs",
        {
            "training_status": "success",
            "$or": [
                {"upload_status": {"$exists": False}},
                {
                    "$and": [
                        {"upload_status": {"$ne": "started"}},
                        {"upload_status": {"$ne": "success"}},
                    ]
                },
            ],
        },
    )
    user_id = new_job.get("user_id", None)
    if user_id is None:
        return "user_id missing", 500

    mongo_upsert("UserTrainingJobs", {"user_id": user_id}, {"upload_ip": ip})

    package_thread = threading.Thread(target=package_model, args=[user_id])
    package_thread.start()
    return "upload started", 201


# Run user inference
@app.route("/run-inferences", methods=["POST"])
def run_inferences():
    generation_jobs = mongo_read(
        "UserTrainingJobs", {"generation_status": "started"}, find_many=True
    )

    if generation_jobs is not None and len(list(generation_jobs)) > 0:
        return "generation job already running", 503

    job = mongo_read(
        "UserTrainingJobs",
        {
            "$or": [
                {"generation_status": {"$exists": False}},
                {"generation_status": {"$ne": "success"}},
            ]
        },
    )

    user_id = job.get("user_id", None)
    if user_id is None:
        return "user_id missing", 500

    inference_thread = threading.Thread(target=generate_all_images, args=[user_id])
    inference_thread.start()
    return "inference started", 201


# Try to call at a specific cadence
@app.route("/check-jobs", methods=["POST"])
def check_jobs():
    check_job_status()
    return "check jobs", 201


# Kickoff user training
@app.route("/train-user-model/<user_id>", methods=["POST"])
def train_user_model(user_id):
    post_request(user_id)


# Upload User Model to s3
@app.route("/upload-model/<user_id>", methods=["POST"])
def upload_model(user_id):
    package_thread = threading.Thread(target=package_model, args=[user_id])
    package_thread.start()
    return "upload started", 201


# Run user inference
@app.route("/run-inference/<user_id>", methods=["POST"])
def run_inference(user_id):
    inference_thread = threading.Thread(target=generate_all_images, args=[user_id])
    inference_thread.start()
    return "inference started", 201


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
