import zlib
from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO, List

from StructIO.structio import BinaryWindow, end_of_stream
from StructIO.vstruct import VStruct
from .properties import WorldObjectProperties
from .shared import buffer_to_str
from .structures import Vector4, Vector3, ObjectReference, Property


@dataclass
class SaveHeader:
    SHARED_LAYOUT = VStruct("3I3v=IQ")
    V5_LAYOUT = VStruct("c")
    V7_LAYOUT = VStruct("=cI")
    V8_LAYOUT = VStruct("=cIvI")

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
        header_args = cls.SHARED_LAYOUT.unpack_stream(stream)
        # version, save_version, build_version, world_type, world_properties, session_name, play_time, save_date
        version = header_args[0]
        # versioned_args: Tuple[bytes, int, str, int] # Here to help visualize the expected layout, not used because we dont want type safety warnings
        if version >= 8:
            versioned_args = cls.V8_LAYOUT.unpack_stream(stream)
        elif version >= 7:
            versioned_args = (*cls.V7_LAYOUT.unpack_stream(stream), None, None)
        elif version >= 5:
            versioned_args = (*cls.V5_LAYOUT.unpack_stream(stream), None, None, None)
        else:
            versioned_args = (None, None, None, None)
        # session_visibility, editor_object_version, mod_metadata, mod_flags = versioned_args # Here to name what each does without looking at the dataclass
        return SaveHeader(*header_args, *versioned_args)


@dataclass
class WorldObjectHeader:
    LAYOUT = VStruct("I3v")
    type: int
    type_path: str
    root_object: str
    instance_name: str

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'WorldObjectHeader':
        args = cls.LAYOUT.unpack_stream(stream)
        return WorldObjectHeader(*args)


@dataclass
class WorldObject:
    SIZE = VStruct("I")
    header: WorldObjectHeader
    properties: List[Property]

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'WorldObject':
        header = WorldObjectHeader.unpack(stream)
        if header.type == 0:
            return StrWorldObject.unpack_data(stream, header)
        elif header.type == 1:
            return DataWorldObject.unpack_data(stream, header)
        else:
            raise ValueError(header.type)

    @classmethod
    def unpack_data(cls, stream: BinaryIO, header: WorldObjectHeader):
        raise NotImplementedError

    def read_properties(self, stream: BinaryIO):
        size = self.SIZE.unpack_stream(stream)[0]
        self.properties = WorldObjectProperties.unpack(stream, size)


@dataclass
class DataWorldObject(WorldObject):
    LAYOUT = VStruct(f"I{Vector4.LAYOUT.format}{Vector3.LAYOUT.format}{Vector3.LAYOUT.format}I")

    need_transform: int
    rotation: Vector4
    position: Vector3
    scale: Vector3
    placed_in_level: int
    parent_object_root: str
    parent_object_name: str
    components: List
    excess_data: bytes

    @classmethod
    def unpack_data(cls, stream: BinaryIO, header: WorldObjectHeader) -> 'DataWorldObject':
        args = cls.LAYOUT.unpack_stream(stream)
        need_transform = args[0]
        rot = args[1:5]
        pos = args[5:8]
        scale = args[8:11]
        placed = args[11]
        return DataWorldObject(header, None, need_transform, Vector4(*rot), Vector3(*pos), Vector3(*scale), placed, None, None, None, None)

    PROP_HEADER_LAYOUT = VStruct("2vI")

    def read_properties(self, stream: BinaryIO):
        size = self.SIZE.unpack_stream(stream)[0]
        with BinaryWindow.slice(stream, size) as window:
            parent_object_root, parent_object_name, component_count = self.PROP_HEADER_LAYOUT.unpack_stream(stream)
            parent_object_root = buffer_to_str(parent_object_root)
            parent_object_name = buffer_to_str(parent_object_name)
            components = []
            for _ in range(component_count):
                component = ObjectReference.unpack(stream)
                components.append(component)

            self.parent_object_root = parent_object_root
            self.parent_object_name = parent_object_name
            self.components = components

            size -= window.tell()
            self.properties = WorldObjectProperties.unpack(window, size)
            excess = window.read()

            if len(excess) > 0:
                self.excess_data = excess
            assert end_of_stream(window)
            # # Should determine if...
            # #   All /Game/FactoryGame/Buildable have excess
            # #   All Blueprints have excess
            # allowed_excess = [
            #     "/Game/FactoryGame/Buildable/Factory/PowerLine/Build_PowerLine.Build_PowerLine_C",
            #     "/Game/FactoryGame/Character/Player/BP_PlayerState.BP_PlayerState_C",
            #     "/Game/FactoryGame/-Shared/Blueprint/BP_CircuitSubsystem.BP_CircuitSubsystem_C",
            #     "/Game/FactoryGame/Buildable/Factory/ConveyorBeltMk1/Build_ConveyorBeltMk1.Build_ConveyorBeltMk1_C",
            #     "/Game/FactoryGame/-Shared/Blueprint/BP_GameState.BP_GameState_C",
            #     "/Game/FactoryGame/-Shared/Blueprint/BP_GameMode.BP_GameMode_C",
            # ]
            #
            # # expected_excess = expected_data.get(self.type_path,0)
            # excess = 0
            # if self.header.type_path in allowed_excess:
            #     assert excess > 0, (excess, "Excess Required", self.header.type_path)
            # else:
            #     assert excess == 0, (excess, "Excess Disallowed", self.header.type_path)
            #


@dataclass
class StrWorldObject(WorldObject):
    LAYOUT = VStruct("v")
    data: str

    @classmethod
    def unpack_data(cls, stream: BinaryIO, header: WorldObjectHeader):
        d = cls.LAYOUT.unpack_stream(stream)[0].decode()
        return StrWorldObject(header, None, d)


@dataclass
class WorldCollectedObject:
    LAYOUT = VStruct("2v")
    type: str
    value: str

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'WorldCollectedObject':
        args = cls.LAYOUT.unpack_stream(stream)
        return WorldCollectedObject(*args)


@dataclass
class SaveBody:
    # Layout is not used because of variable length data (without length-prefixes) between fixed length data
    # Instead VStructs pertaining to common operations are provided instead
    _UINT32 = VStruct("I")

    data_size: int
    world_objects: List[WorldObject]
    world_collected_objects: List[WorldCollectedObject]

    @classmethod
    def unpack(cls, stream: BinaryIO, header: SaveHeader) -> 'SaveBody':
        data_size = cls._UINT32.unpack_stream(stream)[0]
        # Verify body is complete
        before = stream.tell()
        stream.seek(0, 2)
        after = stream.tell()
        assert before + data_size == after, (before + data_size, after)
        stream.seek(before)

        world_object_count = cls._UINT32.unpack_stream(stream)[0]
        world_objects = [WorldObject.unpack(stream) for _ in range(world_object_count)]

        world_objects_property_count = cls._UINT32.unpack_stream(stream)[0]
        assert world_objects_property_count == world_object_count
        for i in range(world_objects_property_count):
            world_objects[i].read_properties(stream)

        world_collected_object_count = cls._UINT32.unpack_stream(stream)[0]
        world_collected_objects = [WorldCollectedObject.unpack(stream) for _ in range(world_collected_object_count)]

        # Verify all data was read
        before = stream.tell()
        stream.seek(0, 2)
        after = stream.tell()
        assert before == after, (before, after)
        stream.seek(before)
        return SaveBody(data_size, world_objects, world_collected_objects)


@dataclass
class ChunkHeader:
    LAYOUT = VStruct("6Q")

    package_file_tag: int
    maximum_chunk_size: int
    compressed_len: int
    uncompressed_len: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'ChunkHeader':
        package_file_tag, maximum_chunk_size, compressed_len, uncompressed_len, compressed_len_verify, uncompressed_len_verify = cls.LAYOUT.unpack_stream(stream)
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
        return_to = self._stream.tell()
        self._stream.seek(self._ptr)

        buffer = self._stream.read(self.header.compressed_len)

        self._stream.seek(return_to)

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
