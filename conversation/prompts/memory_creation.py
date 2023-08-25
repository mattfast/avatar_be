from common.prompt import Prompt


class IsImportantMemoryPrompt(Prompt):
    name = "IsImportantMemoryPrompt"
    version = "0.0.1"
    template = """You are talking with a friend, who just texted you something. Given context in a conversation and what you already know, determine if the recent message contains any new information
that should be committed to memory about the friend, you, or the following entities: NONE. You should err on the side of NO, unless something very important has occurred.
Write YES: reason for decision if so. otherwise, write NO: reason for decision.

Prior Information:
{prior_info}

{conversation}

Recent Texts: {message}

Decision:
"""
