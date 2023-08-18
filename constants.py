from langchain.chat_models.openai import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.llms.openai import OpenAI

OPENAI_API_KEY = "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"
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

fast_model = OpenAI(
    model="text-davinci-003", temperature=0, openai_api_key=OPENAI_API_KEY
)
chat_model = ChatOpenAI(temperature=0, openai_api_key=OPENAI_API_KEY)
simple_model = OpenAI(
    model="text-babbage-001", temperature=0, openai_api_key=OPENAI_API_KEY
)

MODEL_DICT = {"babbage": simple_model, "chat": chat_model, "fast": fast_model}
pronoun_list = [
    "she",
    "he",
    "it",
    "they",
    "him",
    "his",
    "her",
    "hers",
    "their",
    "theirs",
    "its",
    "them",
]
