import struct
from asyncio import Protocol
from typing import Any


class ParsingError(BaseException):
    def __init__(self, stream_pos: int, *args: Any):
        super().__init__(args)
        self.stream_pos = stream_pos

    def __str__(self) -> str:
        return f"@ {self.stream_pos}"


class Nameable(Protocol):
    __name__: str


def packing_args_error(
    cls: Nameable, func: Nameable, received_args: int, expected_args: int
) -> struct.error:
    return struct.error(
        f"`{cls.__name__}.{func.__name__}` expected `{expected_args}` items for packing (got `{received_args}`)"
    )
