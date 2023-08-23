import random
from datetime import datetime

from TikTokApi import TikTokApi

from dbs.mongo import mongo_count, mongo_delete_many, mongo_read, mongo_write_many
from keys import tiktok_cookie
from messaging import send_message
from users import get_users

DESIRED_VIDEOS = 700


async def trending_videos():
    print("about to enter async")
    async with TikTokApi() as api:
        print("creating session")
        await api.create_sessions(ms_tokens=[tiktok_cookie])
        print("session created")
        while True:
            num_videos = mongo_count("TikToks")
            num_to_fetch = DESIRED_VIDEOS - num_videos

            print("NUM VIDEOS AND TO FETCH")
            print(num_videos)
            print(num_to_fetch)

            entries = []
            try:
                async for video in api.trending.videos(count=num_to_fetch):
                    d = video.as_dict
                    now = datetime.now()
                    entries.append(
                        {
                            "videoId": d["id"],
                            "author": d["author"]["uniqueId"],
                            "description": d["desc"],
                            "shareCount": d["stats"]["shareCount"],
                            "playCount": d["stats"]["playCount"],
                            "commentCount": d["stats"]["commentCount"],
                            "createdAt": now,
                            "updatedAt": now,
                        }
                    )
                    print(video)
                    print("\n")
            except:
                print("error fetching videos")

            # find num videos in db
            print("ABOUT TO WRITE")
            if len(entries) > 0:
                mongo_write_many("TikToks", entries)
            num_videos = mongo_count("TikToks")

            print("NEW NUM VIDEOS")
            print(num_videos)

            if num_videos < DESIRED_VIDEOS:
                continue
            else:
                break


async def delete_videos():
    print("about to delete videos")

    # find num to delete
    num_videos = mongo_count("TikToks")
    num_to_delete = num_videos - (DESIRED_VIDEOS - 100)

    # delete videos
    mongo_delete_many("TikToks", number=num_to_delete)


async def send_videos():

    users = list(get_users())
    tiktoks = list(mongo_read("TikToks", {}, find_many=True))
    print(users)

    for user in users:
        print("here")
        if user["number"] != "+12812240743" and user["number"] != "+14803523815":
            continue

        print("here2")

        tiktok = random.choice(tiktoks)
        author = tiktok["author"]
        videoId = tiktok["videoId"]
        url = f"https://www.tiktok.com/@{author}/video/{videoId}"

        print(url)

        send_message("yo, thought you'd like this:", user["number"])
        send_message(url, user["number"])
