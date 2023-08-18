def list_to_convo_prompt(conv_list) -> str:
    """Convert Conversation List to Prompt."""
    orig_str = "Conversation:\n"
    for i, element in enumerate(conv_list):
        orig_str += f"{element.fo}"
    return orig_str
