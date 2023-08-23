
from TikTokApi import TikTokApi
from datetime import datetime

from keys import tiktok_cookie
from dbs.mongo import mongo_count, mongo_write_many, mongo_delete_many

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
                            "updatedAt": now
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

            if num_videos < DESIRED_VIDEOS: continue
            else: break

async def delete_videos():
    print("about to delete videos")

    # find num to delete
    num_videos = mongo_count("TikToks")
    num_to_delete = num_videos - (DESIRED_VIDEOS - 100)

    # delete videos
    mongo_delete_many("TikToks", number=num_to_delete)
