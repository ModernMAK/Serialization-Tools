import struct
from typing import Type


class ParsingError(BaseException):
    def __init__(self, stream_pos: int, *args):
        super().__init__(args)
        self.stream_pos = stream_pos

    def __str__(self):
        return f"@ {self.stream_pos}"


def packing_args_error(cls: Type, func: {__name__}, received_args: int, expected_args: int):
    return struct.error(f"`{cls.__name__}.{func.__name__}` expected `{expected_args}` items for packing (got `{received_args}`)")
