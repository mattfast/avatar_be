
from TikTokApi import TikTokApi
import asyncio
import os

from keys import tiktok_cookie
from dbs.mongo import mongo_write

async def trending_videos():
    print("about to enter async")
    async with TikTokApi() as api:
        print("creating session")
        await api.create_sessions(ms_tokens=[tiktok_cookie], num_sessions=1, sleep_after=3)
        print("session created")
        async for video in api.trending.videos(count=1):
            d = video.as_dict
            mongo_write(
                "TikToks",
                {
                    "videoId": d["id"],
                    "author": d["author"]["uniqueId"],
                    "description": d["desc"], 
                    "shareCount": d["stats"]["shareCount"],
                    "playCount": d["stats"]["playCount"],
                    "commentCount": d["stats"]["commentCount"]
                }
            )
            print(video)
            print("\n")
            #d = video.as_dict
            #for k, v in d.items():
            #    print(k)
            #    print(v)
            #    print("\n")
            #print("\n")


asyncio.run(trending_videos())