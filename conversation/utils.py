import re
from copy import deepcopy


def list_to_convo_prompt(conv_list) -> str:
    """Convert Conversation List to Prompt."""
    orig_str = "Conversation:\n"
    for i, element in enumerate(conv_list):
        orig_str += f"{element.fo}"
    return orig_str


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
