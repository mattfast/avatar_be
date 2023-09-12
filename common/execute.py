from random import random

from langchain.chat_models.openai import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.llms.openai import OpenAI
from langchain.schema import SystemMessage

from common.prompt import Prompt
from constants import MODEL_DICT, chat_models_set
from keys import openai_api_key, secondopenai_api_key


def clean_response(result: str) -> str:
    """Clean result."""
    return result.strip().strip(".").strip().strip('"')


# Add logging for prompt execution
def compile_and_run_prompt(prompt_cls, dict_options: dict, **kwargs):
    try:
        final_prompt = prompt_cls(dict_options)
    except:
        raise ValueError("Missing dictionary Keys")
    if final_prompt.model in chat_models_set:
        return run_chat_prompt(
            final_prompt.template,
            verbose=final_prompt.verbose,
            model=final_prompt.model,
            **kwargs
        )

    if final_prompt.verbose:
        print(final_prompt.template)
    return clean_response(MODEL_DICT[prompt_cls.model](final_prompt.template))


def run_chat_prompt(prompt: str, verbose: bool = False, model: str = "chat", **kwargs):
    messages_to_use = kwargs.get("messages", [])
    system_message = SystemMessage(content=prompt)
    messages_to_use.append(system_message)
    if verbose:
        print(messages_to_use)

    if "4" in model:
        val = random()
        key_to_use = openai_api_key
        if val > 0.8:
            key_to_use = secondopenai_api_key
        MODEL_DICT[model].openai_api_key = key_to_use

    return clean_response(MODEL_DICT[model](messages_to_use).content)
