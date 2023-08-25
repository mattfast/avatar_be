import functools
import random
from datetime import datetime

from TikTokApi import TikTokApi

from common.execute import compile_and_run_prompt
from tiktok.prompt import TagTikToksPrompt
from users import get_users
from dbs.mongo import (
    mongo_bulk_update,
    mongo_count,
    mongo_delete_many,
    mongo_read,
    mongo_write_many,
    mongo_dedupe
)
from messaging import send_message

DESIRED_VIDEOS = 700


async def trending_videos():
    print("about to enter async")
    async with TikTokApi() as api:
        print("creating session")
        await api.create_sessions(num_sessions=1)
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

    # dedupe collection
    res = mongo_dedupe("TikToks", {})
    print("DEDUPED")
    print(res)

    # find additional num to delete
    num_videos = mongo_count("TikToks")
    print("MONGO COUNT")
    print(num_videos)
    num_to_delete = num_videos - (DESIRED_VIDEOS - 100)

    # delete videos
    if num_to_delete > 0:
        mongo_delete_many("TikToks", number=num_to_delete)


async def send_videos():

    users = list(get_users())
    tiktoks = list(mongo_read("TikToks", {}, find_many=True))
    print(users)

    query_list = []
    update_list = []
    for user in users:
        tiktok = random.choice(tiktoks)
        while "tiktoks" in user and tiktok["videoId"] in user["tiktoks"]:
            tiktok = random.choice(tiktoks)

        author = tiktok["author"]
        videoId = tiktok["videoId"]
        url = f"https://www.tiktok.com/@{author}/video/{videoId}"

        new_tiktoks_arr = []
        if "tiktoks" in user:
            print("tiktoks field exists")
            new_tiktoks_arr = user["tiktoks"].append(tiktok["videoId"])
        else:
            print("tiktoks field doesn't exist")
            new_tiktoks_arr = [ tiktok["videoId"] ]

        query_list.append({ "number": user["number"] })
        update_list.append({ "$set": { "tiktoks": new_tiktoks_arr }})
        send_message("hey, thought you'd like this:", user["number"])
        send_message(url, user["number"])
    
    print(query_list)
    print(update_list)
    
    mongo_bulk_update("Users", query_list, update_list)



async def tag_videos():

    print("tagging vids")
    tiktoks = list(mongo_read("TikToks", {"tags": {"$exists": False}}, find_many=True))
    print("TIKTOKS TO TAG:")
    print(len(tiktoks))
    query_list = []
    update_list = []
    for i in range(0, len(tiktoks), 15):
        upper_bound = min(i + 15, len(tiktoks))
        batch = tiktoks[i:upper_bound]
        video_desc_str = functools.reduce(
            lambda a, b: a + f"Video {b['videoId']}: {b['description']}\n", batch, ""
        )
        # print(video_desc_str)
        res = compile_and_run_prompt(
            TagTikToksPrompt, {"video_descriptions": video_desc_str}
        )
        res_list = res.split("\n")
        res_list = [i for i in res_list if i]  # remove empty strings
        for v in res_list:
            try:
                terms = v.split(":")
                videoId = terms[0].split(" ")[1]
                tag = terms[1][1:]
                query_list.append({"videoId": videoId})
                update_list.append({"$set": {"tags": [tag]}})
            except:
                print("ERROR: output not formatted correctly")

    print(query_list)
    print(update_list)

    mongo_bulk_update("TikToks", query_list, update_list)
