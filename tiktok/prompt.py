from common.prompt import Prompt


class TagTikToksPrompt(Prompt):
    name = "TagTikToksPrompt"
    version = "0.0.1"
    template = """Your task is to assign Tiktok videos to categories. You will assign just one category to each TikTok video.

You should sort each TikTok into one of the following categories:

##### Start Categories #####
Category 1: Food

Category 2: Fashion and Beauty

Category 3: Fitness

Category 4: Pets and Animals

Category 5: Pop Culture

Category 6: Travel

Category 7: DIY and Crafting

Category 8: Dance

Category 9: Technology

Category 10: Sports

Category 11: Politics

Category 12: Cleaning and Organization

Category 13: Comedy

Category 14: Miscellaneous
##### End Categories #####

Here are the video numbers and their corresponding descriptions:

##### Start Video Descriptions #####
{video_descriptions}
##### End Video Descriptions #####

Output your answer in the same format as the following examples:

##### Start Examples #####
Video 1: DIY and Crafting

Video 2: Pets and Animals
##### End Examples #####

Answer:
"""


class TikTokLanguagePrompt(Prompt):
    name = "TikTokLanguagePrompt"
    version = "0.0.1"
    template = """Your task is to determine what language a list of Tweets are each written in.

Here are the tweet numbers and their corresponding texts:

##### Start Tweets #####
{video_descriptions}
##### End Tweets #####

Output your answer in the same format as the following examples:

##### Start Examples #####
Tweet 1: Russian

Tweet 2: Chinese

Tweet 3: English
##### End Examples #####

Answer:
"""
