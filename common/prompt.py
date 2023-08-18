class Prompt:
    name: str = ""
    model: str = "chat"
    version: str = "0.0"
    template: str = ""

    def __init__(self, kwargs):
        self.template = self.template.format(**kwargs)
