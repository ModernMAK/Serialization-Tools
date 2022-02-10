import dataclasses
import json
import os
import zlib
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from json import JSONEncoder
from typing import BinaryIO, List

from satisfactory.properties import WorldObjectProperties
from satisfactory.structures import Vector4, Vector3, ObjectReference, Property
from StructIO.structio import StructIO, UInt32

save_file = r"E:\Downloads" + r"\\" + r"waiting_for_coal_research.sav"
StructIO.str_null_terminated_default = True


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
    type: int
    type_path: str
    root_object: str
    instance_name: str
    properties: List[Property]
    type_data:bytes

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'WorldObject':
        with StructIO(stream) as reader:
            type = reader.unpack(UInt32)
            name, property_type, value = [reader.unpack_len_encoded_str() for _ in range(3)]
            # index = reader.unpack(UInt32)

            if type == 0:
                data = reader.unpack_len_encoded_str()
                return StrWorldObject(type, name, property_type, value, None, data,None)
            elif type == 1:
                obj = DataWorldObject.unpack(stream)
            else:
                raise ValueError()
            obj.type = type
            obj.type_path = name
            obj.root_object = property_type
            obj.instance_name = value
            return obj

    def read_properties(self, stream: BinaryIO):
        self.properties, excess = WorldObjectProperties.unpack(stream)
        assert excess == 0, excess


@dataclass
class DataWorldObject(WorldObject):
    need_transform: int
    rotation: Vector4
    position: Vector3
    scale: Vector3
    placed_in_level: int
    parent_object_root: str
    parent_object_name: str
    components: List

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'DataWorldObject':
        with StructIO(stream) as reader:
            need_transform = reader.unpack("I")
            rotation = Vector4.unpack(stream)
            position = Vector3.unpack(stream)
            scale = Vector3.unpack(stream)
            placed_in_level = reader.unpack("I")
            return DataWorldObject(None, None, None, None, None, None, need_transform, rotation, position, scale, placed_in_level, None, None, None)

    def read_properties(self, stream: BinaryIO):
        with StructIO(stream, str_null_terminated=True) as reader:
            read_size = size = reader.unpack("I")
            start = stream.tell()
            parent_object_root = reader.unpack_len_encoded_str()
            parent_object_name = reader.unpack_len_encoded_str()
            component_count = reader.unpack("I")
            components = []
            for _ in range(component_count):
                component = ObjectReference.unpack(stream)
                components.append(component)
            size -= (stream.tell() - start)

            self.parent_object_root = parent_object_root
            self.parent_object_name = parent_object_name
            self.components = components
            self.properties, excess = WorldObjectProperties.unpack(stream, size)


            # Should determine if...
            #   All /Game/FactoryGame/Buildable have excess
            #   All Blueprints have excess
            allowed_excess = [
                "/Game/FactoryGame/Buildable/Factory/PowerLine/Build_PowerLine.Build_PowerLine_C",
                "/Game/FactoryGame/Character/Player/BP_PlayerState.BP_PlayerState_C",
                "/Game/FactoryGame/-Shared/Blueprint/BP_CircuitSubsystem.BP_CircuitSubsystem_C",
                "/Game/FactoryGame/Buildable/Factory/ConveyorBeltMk1/Build_ConveyorBeltMk1.Build_ConveyorBeltMk1_C",
                "/Game/FactoryGame/-Shared/Blueprint/BP_GameState.BP_GameState_C",
                "/Game/FactoryGame/-Shared/Blueprint/BP_GameMode.BP_GameMode_C",
            ]

            # expected_excess = expected_data.get(self.type_path,0)

            if self.type_path in allowed_excess:
                assert excess > 0, (excess, "Excess Required", self.type_path)
            else:
                assert excess == 0, (excess, "Excess Disallowed", self.type_path)

            if excess > 0:
                self.type_data = stream.read(excess)


@dataclass
class StrWorldObject(WorldObject):
    data: str


@dataclass
class WorldCollectedObject:
    type: str
    value: str

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'WorldCollectedObject':
        with StructIO(stream) as reader:
            type = reader.unpack_len_encoded_str()
            value = reader.unpack_len_encoded_str()
            return WorldCollectedObject(type, value)


@dataclass
class SaveBody:
    data_size: int
    world_objects: List[WorldObject]
    world_collected_objects: List[WorldCollectedObject]

    @classmethod
    def unpack(cls, stream: BinaryIO, header: SaveHeader) -> 'SaveBody':
        with StructIO(stream) as reader:
            data_size = reader.unpack(UInt32)
            # Verify we have the full body
            with reader.bookmark():
                now = reader.tell()
                reader.seek(0, 2)
                then = reader.tell()
                assert now + data_size == then, (now + data_size, then)

            world_object_count = reader.unpack(UInt32)

            world_objects = []
            for _ in range(world_object_count):
                world_objects.append(WorldObject.unpack(stream))

            world_objects_property_count = reader.unpack(UInt32)
            assert world_objects_property_count == world_object_count

            for i in range(world_objects_property_count):
                world_object = world_objects[i]
                world_object.read_properties(stream)

            world_collected_object_count = reader.unpack(UInt32)
            world_collected_objects = [WorldCollectedObject.unpack(stream) for _ in range(world_collected_object_count)]
            with reader.bookmark():
                start = reader.tell()
                reader.seek(0, 2)
                end = reader.tell()
                assert start == end, (start, end)

            return SaveBody(data_size, world_objects, world_collected_objects)


@dataclass
class ChunkHeader:
    package_file_tag: int
    maximum_chunk_size: int
    compressed_len: int
    uncompressed_len: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'ChunkHeader':
        with StructIO(stream) as reader:
            _ = stream.tell()
            package_file_tag, maximum_chunk_size = reader.unpack("2Q")
            compressed_len, uncompressed_len = reader.unpack("2Q")
            compressed_len_verify, uncompressed_len_verify = reader.unpack("2Q")
            assert compressed_len == compressed_len_verify, ("COMP", compressed_len, compressed_len_verify)
            assert uncompressed_len == uncompressed_len_verify, ("UNCOMP", uncompressed_len, uncompressed_len_verify)

            return ChunkHeader(package_file_tag, maximum_chunk_size, compressed_len, uncompressed_len)


@dataclass
class Chunk:
    header: ChunkHeader
    _stream: BinaryIO
    _ptr: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'Chunk':
        header = ChunkHeader.unpack(stream)
        ptr = stream.tell()
        stream.seek(header.compressed_len, 1)
        return Chunk(header, stream, ptr)

    def read_body(self, decompress: bool = True) -> bytes:
        reader = StructIO(self._stream)
        with reader.bookmark():
            reader.seek(self._ptr)
            buffer = reader.read(self.header.compressed_len)
            assert len(buffer) == self.header.compressed_len

        if not decompress:
            return buffer

        buffer = zlib.decompress(buffer)
        assert len(buffer) == self.header.uncompressed_len

        return buffer


@dataclass
class DecompressedSave:
    header: SaveHeader
    body: SaveBody


@dataclass
class CompressedSave:
    header: SaveHeader
    chunks: List[Chunk]

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'CompressedSave':
        header = SaveHeader.unpack(stream)
        chunks = []
        while True:
            bookmark = stream.tell()
            if len(stream.read(1)) == 0:
                break
            stream.seek(bookmark)
            chunk = Chunk.unpack(stream)

            chunks.append(chunk)
        return CompressedSave(header, chunks)

    def decompress_body_into(self, buffer: BinaryIO):
        for chunk in self.chunks:
            buffer.write(chunk.read_body())

    def decompress_from(self, buffer: BinaryIO) -> 'DecompressedSave':
        body = SaveBody.unpack(buffer, self.header)
        return DecompressedSave(self.header, body)

    def decompress(self) -> 'DecompressedSave':
        with BytesIO() as buffer:
            self.decompress_body_into(buffer)
            buffer.seek(0)
            return self.decompress_from(buffer)


def dataclass2safedict(obj):
    if dataclasses.is_dataclass(obj):
        result = []
        for f in dataclasses.fields(obj):
            value = dataclass2safedict(getattr(obj, f.name))
            result.append((f.name, value))
        return dict(result)
    elif isinstance(obj, tuple) and hasattr(obj, '_fields'):
        return type(obj)(*[dataclass2safedict(v) for v in obj])
    elif isinstance(obj, (list, tuple)):
        return type(obj)(dataclass2safedict(v) for v in obj)
    elif isinstance(obj, dict):
        return [{"Key": dataclass2safedict(k), "Value": dataclass2safedict(v)} for k, v in obj.items()]
        # return type(obj)((dataclass2safedict(k, dict_factory),
        #                   dataclass2safedict(v, dict_factory))
        #                  for k, v in obj.items())
    else:
        return obj


class FullJsonEncoder(JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclass2safedict(o)
        elif isinstance(o, bytes):
            return o.hex(bytes_per_sep=4,sep=" ")
        elif isinstance(o, Enum):
            return o.value
        else:
            return super().default(o)


if __name__ == "__main__":
    dump = save_file + ".dump"

    with open(save_file, "rb") as reader:
        save = CompressedSave.unpack(reader)
        # print("Compressed:", save)
        if not os.path.exists(dump):
            with open(dump, "w+b") as writer:
                save.decompress_body_into(writer)
                writer.seek(0)
                full_save = save.decompress_from(writer)
        else:
            with open(dump, "rb") as reader:
                full_save = save.decompress_from(reader)

        with open(save_file + '.json', "w") as jsonified:
            json.dump(full_save, jsonified, cls=FullJsonEncoder, indent=4)
