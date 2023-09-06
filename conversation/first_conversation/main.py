import random
import threading
from typing import List

from ai.personality import default_personality
from common.execute import compile_and_run_prompt
from conversation.first_conversation.prompts.responses import (
    AskingAboutMePrompt,
    MusicPrompt,
    NickNamePrompt,
    PreferredResponseTemplate,
    RespondedPrompt,
    SayYesPrompt,
    TriagePrompt,
)
from conversation.message import Message, message_list_to_convo_prompt
from dbs.mongo import mongo_read

NUM_FIRST_CONVO_STEPS = 6

########### FOR RUNNING PROMPTS ###########


def triage_prompt(triage_list: List, user_messages: List[Message]):
    triage = compile_and_run_prompt(
        TriagePrompt,
        {"message": "\n".join([message.content for message in user_messages])},
    ).lower()
    if "positive" in triage:
        triage_list.append("positive")
    elif "negative" in triage:
        triage_list.append("negative")
    else:
        triage_list.append("neutral")


def did_respond_prompt(
    respond_list: List, query_str: str, user_messages: List[Message]
):
    did_respond = compile_and_run_prompt(
        RespondedPrompt,
        {
            "said": query_str,
            "message": "\n".join([message.content for message in user_messages]),
        },
    ).lower()
    if "yes" in did_respond:
        respond_list.append("yes")
    else:
        respond_list.append("no")


def asking_about_me(about_me_list: List, user_messages: List[Message]):
    about_me = compile_and_run_prompt(
        AskingAboutMePrompt,
        {"message": "\n".join([message.content for message in user_messages])},
    ).lower()
    if "yes" in about_me:
        about_me_list.append("yes")
    else:
        about_me_list.append("no")


def run_nickname_prompt(nickname_list: List, user_messages: List[Message]):
    nickname_guidance = "a short, slightly sarcastic nickname that ambiguously makes the person feel better"
    nickname = compile_and_run_prompt(
        NickNamePrompt,
        {
            "personality": default_personality,
            "extra_guidance": nickname_guidance,
            "self_name": "Justin",
            "message": "\n".join([message.content for message in user_messages]),
        },
    ).lower()
    nickname_list.append(nickname)


def said_yes(yes_list: List, just_said: str, user_messages: List[Message]):
    said_yes = compile_and_run_prompt(
        SayYesPrompt,
        {
            "said": just_said,
            "message": "\n".join([message.content for message in user_messages]),
        },
    ).lower()
    if "yes" in said_yes:
        yes_list.append(True)
    else:
        yes_list.append(False)


########### FOR RUNNING PROMPTS ###########
########### FOR SENDING MESSAGES ###########


def send_first_message(
    session_id: str,
    prev_messages: List[Message],
    user_messages: List[Message],
    curr_message,
) -> List[Message]:
    metadata = {"step": 1, "is_first_conversation": True}
    first_message = Message("hey", "ai", session_id, metadata=metadata)
    second_message = Message(
        "what's up? any good plans today?", "ai", session_id, metadata=metadata
    )
    return [first_message, second_message]


def send_second_message(
    session_id: str,
    prev_messages: List[Message],
    user_messages: List[Message],
    curr_message: Message,
) -> List[Message]:
    metadata = {"step": 2, "is_first_conversation": True}
    extra_guidance = """## If the message is about homework just say: "rip"
    """
    negative_neutral_temp = "playful, sarcastic quip that makes fun of their situation in an uplifting way. no more than 6 words."
    pos_template = "playful, slightly sarcastic, earnest quip that makes your friends feel good. no more than 6 words."
    res_messages_str = "\n".join(
        [message.content for message in (user_messages + [curr_message])]
    )
    last_ai_message_to_respond = prev_messages[-1].as_langchain_message()

    all_user_messages = user_messages + [curr_message]
    responded_list = []
    about_me_list = []
    triage_list = []
    respond_thread = threading.Thread(
        target=did_respond_prompt,
        args=[responded_list, "what's up? any good plans today?", all_user_messages],
    )
    about_me_thread = threading.Thread(
        target=asking_about_me, args=[about_me_list, all_user_messages]
    )
    triage_thread = threading.Thread(
        target=triage_prompt, args=[triage_list, all_user_messages]
    )

    respond_thread.start()
    about_me_thread.start()
    triage_thread.start()

    respond_thread.join()
    about_me_thread.join()
    triage_thread.join()

    about_me_message = Message(
        "tbh i don't have much going on", "ai", session_id, metadata=metadata
    )

    if responded_list[0] == "yes":
        triage_val = triage_list[0]
        if triage_val == "positive":
            # only run replace if original does not have exclamation points
            primary_res_content = (
                compile_and_run_prompt(
                    PreferredResponseTemplate,
                    {
                        "self_name": "Justin",
                        "personality": default_personality,
                        "template": pos_template,
                        "extra_guidance": extra_guidance,
                        "message": res_messages_str,
                    },
                    messages=[last_ai_message_to_respond],
                )
                .lower()
                .replace("!", ".")
            )
            secondary_res_content = None
        else:
            nickname_list = []
            nickname_thread = threading.Thread(
                target=run_nickname_prompt, args=[nickname_list, all_user_messages]
            )
            nickname_thread.start()
            primary_res_content = (
                compile_and_run_prompt(
                    PreferredResponseTemplate,
                    {
                        "self_name": "Justin",
                        "personality": default_personality,
                        "template": negative_neutral_temp,
                        "extra_guidance": extra_guidance,
                        "message": res_messages_str,
                    },
                    messages=[last_ai_message_to_respond],
                )
                .lower()
                .replace("!", ".")
            )
            nickname_thread.join()
            secondary_res_content = Message(
                f"i'm going to call you {nickname_list[0]} lol",
                "ai",
                session_id,
                metadata=metadata,
            )

        primary_res_message = Message(
            primary_res_content, "ai", session_id, metadata=metadata
        )
        final_message = Message(
            "you go to lex right?", "ai", session_id, metadata=metadata
        )
        return_arr = [primary_res_message]
        if secondary_res_content is not None:
            return_arr = return_arr + [secondary_res_content]
        return_arr = return_arr + [final_message]
        if about_me_list[0] == "yes":
            return_arr = [about_me_message] + return_arr
        return return_arr
    else:
        return []


# Affirm that they knew it, didn't know went to a school + ask about dogs + cats
def send_third_message(
    session_id: str,
    prev_messages: List[Message],
    user_messages: List[Message],
    curr_message,
) -> List[Message]:
    metadata = {"step": 3, "is_first_conversation": True}
    all_user_messages = user_messages + [curr_message]

    just_said = "you go to lex, right?"
    said_yes = compile_and_run_prompt(
        SayYesPrompt,
        {
            "said": just_said,
            "message": "\n".join([message.content for message in all_user_messages]),
        },
    ).lower()
    if "yes" in said_yes:
        first_message = Message(
            "sweet, lucky guess ig", "ai", session_id, metadata=metadata
        )
    else:
        first_message = Message(
            "damn. promise i'm not creeping lmao", "ai", session_id, metadata=metadata
        )
    final_message = Message(
        "anyways, do you like dogs or cats?", "ai", session_id, metadata=metadata
    )
    return [first_message, final_message]


# Send tiktoks + music rec question
def send_fourth_message(
    session_id: str,
    prev_messages: List[Message],
    user_messages: List[Message],
    curr_message,
) -> List[Message]:
    metadata = {"step": 4, "is_first_conversation": True}
    say_yes_list = []
    all_user_messages = user_messages + [curr_message]
    res_messages_str = "\n".join(
        [message.content for message in (user_messages + [curr_message])]
    )
    said_yes(say_yes_list, "anyways, do you like dogs or cats?", all_user_messages)
    last_ai_message_to_respond = prev_messages[-1].as_langchain_message()
    if say_yes_list[0]:
        first_message = Message("nice, same", "ai", session_id, metadata=metadata)
    else:
        response_template = 'short, clever response that pokes fun at their dislike. phrased as "guess [fill in response]" no longer than 8 words.'
        funny_res = (
            compile_and_run_prompt(
                PreferredResponseTemplate,
                {
                    "self_name": "Justin",
                    "personality": default_personality,
                    "template": response_template,
                    "extra_guidance": "",
                    "message": res_messages_str,
                },
                messages=[last_ai_message_to_respond],
            )
            .lower()
            .replace("!", ".")
        )
        first_message = Message(
            f"bummer. {funny_res}", "ai", session_id, metadata=metadata
        )

    tiktoks = list(mongo_read("TikToks", {"tags": "Pets and Animals"}, find_many=True))
    tiktok = random.choice(tiktoks)
    author = tiktok["author"]
    videoId = tiktok["videoId"]
    url = f"https://www.tiktok.com/@{author}/video/{videoId}"

    preface = "let me know what you think of this tiktok"

    ai_tiktok_preface = Message(preface, "ai", session_id, metadata=metadata)
    ai_tiktok_url = Message(
        url, "ai", session_id, message_type="TikTok", metadata=metadata
    )
    final_message = Message(
        "btw, what kind of music do you like?", "ai", session_id, metadata=metadata
    )
    return [first_message, ai_tiktok_preface, ai_tiktok_url, final_message]


# Send out music rec
def send_fifth_message(
    session_id: str,
    prev_messages: List[Message],
    user_messages: List[Message],
    curr_message,
) -> List[Message]:
    metadata = {"step": 5, "is_first_conversation": False}
    rec = (
        compile_and_run_prompt(
            MusicPrompt,
            {
                "preferences": "\n".join(
                    [message.content for message in user_messages + [curr_message]]
                )
            },
        )
        .replace("'", "")
        .replace('"', "")
    )
    response = "sweet, check out " + rec
    ai_first_message = Message(response, "ai", session_id, metadata=metadata)
    return [ai_first_message]


########### FOR SENDING MESSAGES ###########


FIRST_CONVO_STEP_MAP = {
    1: send_first_message,
    2: send_second_message,
    3: send_third_message,
    4: send_fourth_message,
    5: send_fifth_message,
}
