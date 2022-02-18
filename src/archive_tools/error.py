class ParsingError(BaseException):
    def __init__(self, *args):
        self.stream_pos = args[0]
        self.args = args[1:] if len(args) > 1 else None

    def __str__(self):
        return f"@ {self.stream_pos}"
