class ParsingError(BaseException):
    def __init__(self, stream_pos: int, *args):
        super().__init__(args)
        self.stream_pos = stream_pos

    def __str__(self):
        return f"@ {self.stream_pos}"
