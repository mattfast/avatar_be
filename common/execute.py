from langchain.schema import SystemMessage

from common.prompt import Prompt
from constants import MODEL_DICT


def clean_response(result: str) -> str:
    """Clean result."""
    return result.strip().strip(".").strip().strip('"')


# Add logging for prompt execution
def compile_and_run_prompt(prompt_cls, dict_options: dict, **kwargs):
    try:
        formatted_prompt = prompt_cls(dict_options).template
    except:
        raise ValueError("Missing dictionary Keys")
    if prompt_cls.model == "chat":
        run_chat_prompt(formatted_prompt, **kwargs)
    return clean_response(MODEL_DICT[prompt_cls.model](formatted_prompt))


def run_chat_prompt(prompt: str, **kwargs):
    messages_to_use = kwargs.get("messages", [])
    system_message = SystemMessage(content=prompt)
    messages_to_use.append(system_message)
    return clean_response(MODEL_DICT["chat"](messages_to_use).content)
