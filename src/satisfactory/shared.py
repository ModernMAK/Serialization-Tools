class NonePropertyError(Exception):
    pass


__NULL = b'\x00'
__NULL_INT = 0


def buffer_to_str(buffer: bytes, strip_null: bool = True, **kwargs) -> str:
    if strip_null and len(buffer) > 0 and buffer[-1] == __NULL_INT:
        buffer = buffer[:-1]
    return buffer.decode(**kwargs)


def str_to_buffer(buffer: str, enforce_null: bool = True, **kwargs) -> bytes:
    if enforce_null and len(buffer) > 0 and buffer[-1] != __NULL_INT:
        buffer += __NULL
    return buffer.encode(**kwargs)
