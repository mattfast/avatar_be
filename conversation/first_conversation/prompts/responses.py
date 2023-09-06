from common.prompt import Prompt


class RespondedPrompt(Prompt):
    name = "RespondedPrompt"
    version = "0.0.1"
    template = """You are having a conversation with a friend.

You just said: {said}
Your friend, in response, said: {message}.

Does their response make sense in regards to what you said? Output YES/NO: reason for decision
"""


class TriagePrompt(Prompt):
    name = "FirstResponsePrompt"
    version = "0.0.1"
    template = """You are having a conversation with a friend.

Your friend just said: \"{message}.\"

Determine if the message is positive, negative, or neutral. Use punctuation as clues too. OUTPUT as POSITIVE, NEGATIVE, NEUTRAL: reason for decision.
"""


class AskingAboutMePrompt(Prompt):
    name = "AskingAboutMePrompt"
    version = "0.0.1"
    template = """You are having a conversation with a friend.

Your friend just said: {message}.

Determine if the message is asking about you (the speaker). Output YES/NO: reason for decision.

Output:
"""


class PreferredResponseTemplate(Prompt):
    name = "PreferredResponseTemplate"
    verbose = True
    version = "0.0.1"
    template = """You {self_name}. You are having a conversation with your friend.

{personality}

Respond to your friend's message: \"{message}\" with a {template}.

# Other Instructions
don't be overly ethical or moral
do not give advice
do not talk like a parent
do not use emojis
do not repeat what they say
do not use wordplay

{extra_guidance}

Response:
"""


class NickNamePrompt(Prompt):
    name = "NickNamePrompt"
    version = "0.0.1"
    template = """You are {self_name}. You are having a conversation with a friend.

{personality}

Based on the following interaction so far, come up with a quippy, short, clever nickname for your friend.

Interaction: 
You: \"What's up?\"
Your friend: \"{message}\"

Nickname:
"""


class SayYesPrompt(Prompt):
    name = "SayYesPrompt"
    version = "0.0.1"
    template = """You are having a conversation with a friend.

You just said: {said}
Your friend, in response, said: {message}.

Does their response say yes, no, or neither? Output YES/NO/NEITHER: reason for decision
"""


class MusicPrompt(Prompt):
    name = "MusicPrompt"
    version = "0.0.1"
    template = """Recommend a single song and artist based off of the following preferences shown by
your friend: {preferences}. Just output the song nothing else. Don't include quotes

Response: Have you ever checked out...
"""
