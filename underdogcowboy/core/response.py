class Response:
    def __init__(self, text: str):
        self.text = text

    def __str__(self):
        return self.text

    def __repr__(self):
        return f"Response({self.text!r})"

    def __or__(self, agent):
        return agent.assess(self.text)