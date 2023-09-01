from common.prompt import Prompt


class EmotionExtractionPrompt(Prompt):
    name = "EmotionExtractionPrompt"
    version = "0.0.1"
    template = """Using the conversation as context, output the two main emotions expressed by the speaker in the last text of the conversation in a comma separated list:

## Start Context ##
{conversation}
## End Context ##

Last Text: {texts}
Emotions Present:"""


class TopicSentimentPrompt(Prompt):
    name = "TopicSentimentPrompt"
    version = "0.0.1"
    template = """Using the conversation as context, output the main emotions expressed by the speaker in the conversation. Output as a single word feeling.
"""


class PersonIntentPrompt(Prompt):
    name = "PersonIntentPrompt"
    verbose = True
    version = "0.0.1"
    template = """Using the conversation as context, output the intent expressed by the speaker in the conversation. 

## Start Example ##
Human: Does Nike make running shoes?
Assistant: The speaker's intent is to inquiring about whether Nike, a specific brand, manufactures running shoes because they are asking about Nike's running shoes.
## End Example ##

Output in one sentence as: "The speaker's intent is... because..." """


class PersonalityUpdatePrompt(Prompt):
    name = "PersonalityUpdatePrompt"
    version = "0.0.1"
    template = """You are texting a friend. Using the last sentence they said and their current personality description as context, output an updated personality description as a short, comma
separated list. Include Likes, dislikes, and general behavior. If nothing changed, output the personality description provided. Just output the description. Nothing else.

Personality Description: {description}
Last Sentence: {sentence}

Personality Update:
"""
