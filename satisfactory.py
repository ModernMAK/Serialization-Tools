import zlib
from dataclasses import dataclass
from io import BytesIO
from struct import Struct
from typing import BinaryIO, List
from main import StructIO, UInt32

save_file = r"C:\Users\moder\Downloads\waiting_for_coal_research.sav"


@dataclass
class SaveHeader:
    header_version: int
    save_version: int
    build_version: int
    world_type: str
    world_properties: str
    session_name: str
    play_time: int
    save_date: int
    session_visibility: bytes
    editor_version: int
    meta: str
    data_size: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'SaveHeader':
        with StructIO(stream) as reader:
            version, save_version, build_version = reader.unpack("3I")
            world_type, world_properties, session_name = [reader.unpack_len_encoded_str() for _ in range(3)]
            play_time, save_date = reader.unpack("=IQ")  # = disables alignment; which makes the unpack 12 instead of 16
            session_visibility = reader.unpack("c") if version >= 5 else None
            editor_object_version = reader.unpack(UInt32) if version >= 7 else None
            mod_metadata, mod_flags = (reader.unpack_len_encoded_str(), reader.unpack(UInt32)) if version >= 8 else (None, None)
            return SaveHeader(version, save_version, build_version, world_type, world_properties, session_name, play_time, save_date, session_visibility, editor_object_version, mod_metadata, mod_flags)


@dataclass
class WorldObject:
    type:int
    name: str
    property_type: str
    value: str
    index:int
    data: bytes

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'WorldObject':
        with StructIO(stream) as reader:
            type = reader.unpack(UInt32)
            name, property_type, value = [reader.unpack_len_encoded_str() for _ in range(3)]
            index = reader.unpack(UInt32)
            data = reader.read(16*3-4)
            return WorldObject(type, name, property_type, value,index,data)


@dataclass
class WorldObjectProperty:
    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'WorldObjectProperty':
        return None


@dataclass
class WorldCollectedObject:
    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'WorldCollectedObject':
        return None


@dataclass
class ChunkBody:
    unknown: int
    world_objects: List[WorldObject]
    world_objects_properties: List[WorldObjectProperty]
    world_collected_objects: List[WorldCollectedObject]

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'ChunkBody':
        with StructIO(stream) as reader:
            unknown = reader.unpack(UInt32)

            world_object_count = reader.unpack(UInt32)
            world_objects = [WorldObject.unpack(stream) for _ in range(world_object_count)]

            world_objects_property_count = reader.unpack(UInt32)
            world_objects_properties = [WorldObjectProperty.unpack(stream) for _ in range(world_objects_property_count)]

            world_collected_object_count = reader.unpack(UInt32)
            world_collected_objects = [WorldCollectedObject.unpack(stream) for _ in range(world_collected_object_count)]

            return ChunkBody(unknown, world_objects, world_objects_properties, world_collected_objects)


@dataclass
class ChunkHeader:
    package_file_tag: int
    maximum_chunk_size: int
    compressed_len: int
    uncompressed_len: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'ChunkHeader':
        with StructIO(stream) as reader:
            package_file_tag, maximum_chunk_size = reader.unpack("2Q")
            compressed_len, uncompressed_len = reader.unpack("2Q")
            compressed_len_verify, uncompressed_len_verify = reader.unpack("2Q")
            assert compressed_len == compressed_len_verify
            assert uncompressed_len_verify == uncompressed_len_verify
            return ChunkHeader(package_file_tag, maximum_chunk_size, compressed_len, uncompressed_len)


@dataclass
class Chunk:
    header: ChunkHeader
    body: ChunkBody

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'Chunk':
        header = ChunkHeader.unpack(stream)

        compressed_data = stream.read(header.compressed_len)
        assert len(compressed_data) == header.compressed_len

        uncompressed_data = zlib.decompress(compressed_data)
        assert len(uncompressed_data) == header.uncompressed_len

        with open(r"C:\Users\moder\Downloads\waiting_for_coal_research.sav.data","wb") as h:
            h.write(uncompressed_data)

        with BytesIO(uncompressed_data) as buffer:
            body = ChunkBody.unpack(buffer)

        return Chunk(header, body)

@dataclass
class Save:
    header:SaveHeader
    chunks:List[Chunk]

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'Save':
        header = SaveHeader.unpack(stream)
        chunks = []
        while True:
            bookmark = stream.tell()
            if len(stream.read(1)) == 0:
                break
            stream.seek(bookmark)
            chunk = Chunk.unpack(stream)

            chunks.append(chunk)
        return Save(header, chunks)


if __name__ == "__main__":
    with open(save_file, "rb") as reader:
        save = Save.unpack(reader)
        print(save)
        print(reader.tell().to_bytes(4, "big").hex(bytes_per_sep=1, sep=" "))
