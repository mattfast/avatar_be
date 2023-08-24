import re
from copy import deepcopy
from typing import List


def clean_sentence(sentence):
    copy = deepcopy(sentence)

    for replacement in common_replacements:
        copy = re.sub(
            rf"\b{replacement}\b", common_replacements[replacement], copy, flags=re.I
        )
    return copy


def clean_json_list_output(raw_output):
    return_vals = []
    if "none" not in raw_output.lower():
        return_vals = [
            return_val.strip().replace("\"'_.`", "")
            for return_val in raw_output.strip("[]").lower().split(",")
        ]
    return return_vals


common_replacements = {
    "wbu": "what about you",
    "u": "you",
    "r": "are",
    "ur": "your",
    "gud": "good",
    "omg": "oh my god",
    "cus": "because",
    "idt": "i don't think",
    "btw": "by the way",
    "abt": "about",
    "idk": "i don't know",
}


def format_memories(memories: List[dict]) -> str:
    if len(memories) == 0:
        return "None"

    format_str = ""
    for i, match in enumerate(memories):
        match_metadata = match.get("metadata", {})
        format_str += f"Memory {i}: {match_metadata.get('content', 'None')}\n"
    return format_str
