from common.prompt import Prompt


class RespondedPrompt(Prompt):
    name = "RespondedPrompt"
    version = "0.0.1"
    template = """You are having a conversation with a friend.

You just said: {said}
Your friend said, in response, a couple things: {message}.

Does their response make sense in regards to what you said? Output YES/NO: reason for decision
"""


class IsFamousNamePrompt(Prompt):
    name = "IsFamousNamePrompt"
    version = "0.0.1"
    template = """You are having a conversation.
    
The person just told you that their name is: {name}
     
Is the name above a famous celebrity, well-known historical figure, or name from pop culture? Output YES/NO: reason for decision
"""


class ArtistOrGenrePrompt(Prompt):
    name = "ArtistOrGenrePrompt"
    version = "0.0.1"
    template = """You are having a conversation about music with your friend.
     
Your friend just said: {message}

Does the message above mention a specific artist/song.
Output YES/NO: reason for decision
"""


class AskedAnyQuestionsPrompt(Prompt):
    name = "AskedAnyQuestionsPrompt"
    version = "0.0.1"
    template = """You are having a conversation with a friend.

Your friend said: {message}.

Are they asking any questions you need to respond to? Output YES/NO: reason for decision
"""


class TriagePrompt(Prompt):
    name = "FirstResponsePrompt"
    model = "gpt-4"
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
    model = "gpt-4"
    version = "0.0.1"
    template = """You are {self_name}. You are having a conversation with your friend.

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


class SayYesPrompt(Prompt):
    name = "SayYesPrompt"
    model = "gpt-4"
    verbose = True
    version = "0.0.1"
    template = """You are having a conversation with a friend.

You just said: "{said}"
Your friend, in response, said: "{message}."
You want to know if they said yes to the following question: {question}. Because you said multiple things, your friends response might be not be clear. That's ok. Output yes, if there is a chance they said yes.


Could your friends response in any way answer yes to the question you asked? 
Only output NO if they explictly said NO. Output YES in all other cases. Output YES/NO: reason for decision.

Now decide:
"""


class MusicPrompt(Prompt):
    name = "NickNamePrompt"
    version = "0.0.1"
    template = """Recommend a niche artist based off of the following preferences shown by
your friend: {preferences}. Just output the artist nothing else. Don't include quotes

Artist Name:
"""
