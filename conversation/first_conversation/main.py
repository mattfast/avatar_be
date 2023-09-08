import random
import threading
from typing import List, Tuple

from ai.personality import default_personality
from common.execute import compile_and_run_prompt
from conversation.first_conversation.prompts.responses import (
    AskedAnyQuestionsPrompt,
    AskingAboutMePrompt,
    MusicPrompt,
    PreferredResponseTemplate,
    RespondedPrompt,
    SayYesPrompt,
    TriagePrompt,
)
from conversation.message import Message, message_list_to_convo_prompt
from dbs.mongo import mongo_read
from spotify.logic import get_recommendation

NUM_FIRST_CONVO_STEPS = 6

########### FOR RUNNING PROMPTS ###########


def triage_prompt(triage_list: List, user_messages: List[Message]):
    triage = compile_and_run_prompt(
        TriagePrompt,
        {"message": ". ".join([message.content for message in user_messages])},
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
            "message": ". ".join([message.content for message in user_messages]),
        },
    ).lower()
    if "yes" in did_respond:
        respond_list.append("yes")
    else:
        respond_list.append("no")


def asked_questions_prompt(questions_list: List, user_messages: List[Message]):
    did_respond = compile_and_run_prompt(
        AskedAnyQuestionsPrompt,
        {
            "message": ". ".join([message.content for message in user_messages]),
        },
    ).lower()
    if "yes" in did_respond:
        questions_list.append(True)
    else:
        questions_list.append(False)


def said_yes(
    yes_list: List, just_said: str, user_messages: List[Message], question: str
):
    said_yes = compile_and_run_prompt(
        SayYesPrompt,
        {
            "said": just_said,
            "message": ". ".join([message.content for message in user_messages]),
            "question": question,
        },
    ).lower()
    print(said_yes)
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
) -> Tuple[bool, List[Message]]:
    metadata = {"step": 1, "is_first_conversation": True}
    first_message = Message("hey!", "ai", session_id, metadata=metadata)
    second_message = Message(
        "i'm your high school's ai", "ai", session_id, metadata=metadata
    )
    third_message = Message("you go to lex right?", "ai", session_id, metadata=metadata)
    return False, [first_message, second_message, third_message]


def send_second_message(
    session_id: str,
    prev_messages: List[Message],
    user_messages: List[Message],
    curr_message,
) -> Tuple[bool, List[Message]]:
    metadata = {"step": 2, "is_first_conversation": True}
    all_user_messages = user_messages + [curr_message]
    final_message = Message(
        "anyways, what's your name?", "ai", session_id, metadata=metadata
    )

    respond_list = []
    just_said = "you go to lex, right?"
    did_respond_prompt(respond_list, "you go to lex right?", all_user_messages)
    print(f"DID RESPOND: {respond_list[0]}")
    if respond_list[0] == "no":
        return True, [final_message]

    additional_ask_list = []
    ask_thread = threading.Thread(
        target=asked_questions_prompt, args=[additional_ask_list, all_user_messages]
    )
    ask_thread.start()

    said_yes = compile_and_run_prompt(
        SayYesPrompt,
        {
            "said": just_said,
            "message": ". ".join([message.content for message in all_user_messages]),
            "question": just_said,
        },
    ).lower()
    if "yes" in said_yes:
        first_message = Message(
            "sweet, lucky guess ig", "ai", session_id, metadata=metadata
        )
        second_message = Message(
            "jk, i'm only for lex students rn", "ai", session_id, metadata=metadata
        )
        third_message = None
    else:
        first_message = Message(
            "damn. my bad lmao", "ai", session_id, metadata=metadata
        )
        second_message = Message(
            "i'm only for lex students rn", "ai", session_id, metadata=metadata
        )
        third_message = Message(
            "you can still try me out though", "ai", session_id, metadata=metadata
        )

    starting_arr = [first_message, second_message]
    if third_message is not None:
        starting_arr = starting_arr + [third_message]
    starting_arr += [final_message]
    ask_thread.join()

    should_continue_conv = additional_ask_list[0]

    return should_continue_conv, starting_arr


def send_third_message(
    session_id: str,
    prev_messages: List[Message],
    user_messages: List[Message],
    curr_message: Message,
) -> Tuple[bool, List[Message]]:
    metadata = {"step": 3, "is_first_conversation": True}
    all_user_messages = user_messages + [curr_message]
    respond_list = []
    just_said = "what's your name?"
    did_respond_prompt(respond_list, just_said, all_user_messages)
    print(f"DID RESPOND: {respond_list[0]}")

    second_message = Message(
        "any good plans today?", "ai", session_id, metadata=metadata
    )

    if respond_list[0] == "no":
        return True, [second_message]

    first_message = Message("great to meet you!", "ai", session_id, metadata=metadata)
    return False, [first_message, second_message]


# Affirm that they knew it, didn't know went to a school + ask about dogs + cats
def send_fourth_message(
    session_id: str,
    prev_messages: List[Message],
    user_messages: List[Message],
    curr_message,
) -> Tuple[bool, List[Message]]:
    metadata = {"step": 4, "is_first_conversation": True}
    extra_guidance = """## If the message is only about homework just say: "rip, which subjects?"
    ## If the message mentions a specific sport, say something, like: "how long have you played [specific sport]?",
    ## If the message is about any other sort of extracurricular (like theater), ask a specific, short question about that extracurricular
    ## if the message mentions hanging out with someone: if a specific activity is mentioned: ask a specific, short question about their activity, otherwise ask what they are doing
    ## if the message mentions going to a specific class: ask if they like they like [[specific class]], otherwise if them message doesn't mention the subject, ask which class they are going to
    """
    template = "short, compassionate, interested question. do not rhyme. do not name or refer to your friend at all. only say one thing. no more than 6 words."

    personal_experience_guidance = """## If the message is only about homework just say: "if it's [[choose random high school subject]], good luck"
    ## If the message mentions a specific sport, say something, like: "idk how you do that. i could never have the [[one skill required to  play sport]]",
    ## If the message is about any other sort of extracurricular, leave a short comment on how fun their extracurricular is, eg. "sounds fun" DO NOT LEAD WITH A QUESTION
    ## if the message mentions hanging out with someone: leave a short comment on how you wish you could join them
    ## if the message mentions going to class: i always loved [[insert name of high school subject here]]
    """
    personal_experience_temp = "short, nice, interesting compliment. do not rhyme. DO NOT LEAD WITH A question. just say something. do not name or refer to your friend at all. only say one thing. DO NOT START WITH A QUESTION. no more than 8 words."

    res_messages_str = "\n".join(
        [message.content for message in (user_messages + [curr_message])]
    )
    last_ai_message_to_respond = prev_messages[-1].as_langchain_message()

    all_user_messages = user_messages + [curr_message]
    responded_list = []
    respond_thread = threading.Thread(
        target=did_respond_prompt,
        args=[
            responded_list,
            "great to meet you! any good plans today?",
            all_user_messages,
        ],
    )

    respond_thread.start()
    respond_thread.join()
    print(f"DID RESPOND: {responded_list[0]}")

    final_message = Message(
        "anyways, are u a dog or a cat person?", "ai", session_id, metadata=metadata
    )

    if responded_list[0] == "yes":
        # only run replace if original does not have exclamation points
        primary_res_content = (
            compile_and_run_prompt(
                PreferredResponseTemplate,
                {
                    "self_name": "Justin",
                    "personality": default_personality,
                    "template": template,
                    "extra_guidance": extra_guidance,
                    "message": res_messages_str,
                },
                messages=[last_ai_message_to_respond]
                + [message.as_langchain_message() for message in all_user_messages],
            )
            .lower()
            .replace("!", ".")
        )

        # only run replace if original does not have exclamation points
        secondary_res = (
            compile_and_run_prompt(
                PreferredResponseTemplate,
                {
                    "self_name": "Justin",
                    "personality": default_personality,
                    "template": personal_experience_temp,
                    "extra_guidance": personal_experience_guidance,
                    "message": res_messages_str,
                },
                messages=[last_ai_message_to_respond]
                + [message.as_langchain_message() for message in all_user_messages],
            )
            .lower()
            .replace("!", ".")
        )

        primary_res_message = Message(
            primary_res_content, "ai", session_id, metadata=metadata
        )
        secondary_res_message = Message(
            secondary_res, "ai", session_id, metadata=metadata
        )
        return_arr = [secondary_res_message, primary_res_message]
        return False, return_arr + [final_message]
    return True, [final_message]


# Send tiktoks + music rec question
def send_fifth_message(
    session_id: str,
    prev_messages: List[Message],
    user_messages: List[Message],
    curr_message,
) -> Tuple[bool, List[Message]]:
    metadata = {"step": 5, "is_first_conversation": True}
    say_yes_list = []
    all_user_messages = user_messages + [curr_message]

    break_id = 0
    for i in range(len(prev_messages) - 1, -1, -1):
        if prev_messages[i].role == "ai" and prev_messages[i - 1].role != "ai":
            break_id = i
            break

    ai_initiations = ". ".join(
        [message.content for message in prev_messages[break_id:]]
    )
    print(ai_initiations)
    res_messages_str = ". ".join(
        [message.content for message in (user_messages + [curr_message])]
    )
    said_yes(
        say_yes_list,
        ai_initiations,
        all_user_messages,
        "anyways, are u a dog or a cat person?",
    )

    last_messages_to_respond = [
        message.as_langchain_message()
        for message in prev_messages[break_id:] + all_user_messages
    ]
    if say_yes_list[0]:
        first_message = Message("same haha", "ai", session_id, metadata=metadata)
    else:
        response_template = 'short, funny response about their dislike of dogs and cats. phrased as "guess you\'re more of a [fill in response]" no longer than 6 words.'
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
                messages=last_messages_to_respond,
            )
            .lower()
            .replace("!", ".")
        )
        first_message = Message(funny_res, "ai", session_id, metadata=metadata)

    tiktoks = list(mongo_read("TikToks", {"tags": "Pets and Animals"}, find_many=True))
    tiktok = random.choice(tiktoks)
    author = tiktok["author"]
    videoId = tiktok["videoId"]
    url = f"https://www.tiktok.com/@{author}/video/{videoId}"

    preface = "found this tiktok lmk what you think"

    ai_tiktok_preface = Message(preface, "ai", session_id, metadata=metadata)
    ai_tiktok_url = Message(
        url, "ai", session_id, message_type="TikTok", metadata=metadata
    )
    final_message = Message(
        "btw, what kind of music do you like?", "ai", session_id, metadata=metadata
    )
    return False, [first_message, ai_tiktok_preface, ai_tiktok_url, final_message]


# Send out music rec
def send_sixth_message(
    session_id: str,
    prev_messages: List[Message],
    user_messages: List[Message],
    curr_message,
) -> Tuple[bool, List[Message]]:
    metadata = {"step": 6, "is_first_conversation": False}

    all_user_messages = user_messages + [curr_message]
    responded_list = []
    did_respond_prompt(
        responded_list,
        "btw, what kind of music do you like?",
        all_user_messages,
    )
    print(f"DID RESPOND: {responded_list[0]}")

    if responded_list[0] == "no":
        return True, []

    rec = (
        compile_and_run_prompt(
            MusicPrompt,
            {
                "preferences": ". ".join(
                    [message.content for message in user_messages + [curr_message]]
                )
            },
        )
        .replace("'", "")
        .replace('"', "")
    )
    print(rec)
    song_recs = get_recommendation(rec, "artist")
    song = song_recs[0]
    print(song)
    first_message = Message("actually same", "ai", session_id, metadata=metadata)
    response = f"check out {song['name'].lower()} by {song['artist_names'][0].lower()}. lmk what you think"
    ai_first_message = Message(response, "ai", session_id, metadata=metadata)
    ai_url_message = Message(song["spotify_url"], "ai", session_id, metadata=metadata)
    return False, [first_message, ai_first_message, ai_url_message]


########### FOR SENDING MESSAGES ###########


FIRST_CONVO_STEP_MAP = {
    1: send_first_message,
    2: send_second_message,
    3: send_third_message,
    4: send_fourth_message,
    5: send_fifth_message,
    6: send_sixth_message,
}
