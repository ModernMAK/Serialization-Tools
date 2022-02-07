from dataclasses import dataclass
from typing import List, ForwardRef, BinaryIO, Dict, Callable

from structio import StructIO

Property = ForwardRef("Property")


@dataclass
class Vector2:
    x: float
    y: float

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int = None) -> 'Vector2':
        with StructIO(stream) as reader:
            xy = reader.unpack("2f")
            return Vector2(*xy)

    def pack(self, stream: BinaryIO) -> int:
        with StructIO(stream) as writer:
            return writer.pack("2f", (self.x, self.y))


@dataclass
class Vector3(Vector2):
    z: float

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int = None) -> 'Vector3':
        with StructIO(stream) as reader:
            xyz = reader.unpack("3f")
            return Vector3(*xyz)

    def pack(self, stream: BinaryIO) -> int:
        with StructIO(stream) as writer:
            return writer.pack("3f", (self.x, self.y, self.z))


@dataclass
class Vector4(Vector3):
    w: float

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int = None) -> 'Vector4':
        with StructIO(stream) as reader:
            xyzw = reader.unpack("4f")
            return Vector4(*xyzw)

    def pack(self, stream: BinaryIO) -> int:
        with StructIO(stream) as writer:
            return writer.pack("4f", (self.x, self.y, self.z, self.w))

@dataclass
class ObjectReference:
    level:str
    path:str

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int = None) -> 'ObjectReference':
        with StructIO(stream) as reader:
            level = reader.unpack_len_encoded_str()
            path = reader.unpack_len_encoded_str()
            return ObjectReference(level,path)

    def pack(self, stream: BinaryIO) -> int:
        with StructIO(stream) as writer:
            written = writer.pack_len_encoded_str(self.level)
            written += writer.pack_len_encoded_str(self.path)
            return written
@dataclass
class Color32:
    r: int
    g: int
    b: int
    a: int

    @staticmethod
    def _is_byte(value: int) -> bool:
        return 0 <= value <= 255

    @property
    def is_valid(self):
        return self._is_byte(self.r) and self._is_byte(self.g) and self._is_byte(self.b) and self._is_byte(self.a)

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int = None) -> 'Color32':
        with StructIO(stream) as reader:
            rgba = reader.unpack("4c")
            return Color32(*rgba)

    def pack(self, stream: BinaryIO) -> int:
        if not self.is_valid:
            raise ValueError(self)
        with StructIO(stream) as writer:
            return writer.pack("4c", (self.r, self.g, self.b, self.a))


@dataclass
class Color:
    r: float
    g: float
    b: float
    a: float

    @staticmethod
    def _is_valid(value: float) -> bool:
        return 0 <= value <= 1

    @property
    def is_valid(self):
        return self._is_valid(self.r) and self._is_valid(self.g) and self._is_valid(self.b) and self._is_valid(self.a)

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int = None) -> 'Color':
        with StructIO(stream) as reader:
            rgba = reader.unpack("4f")
            return Color(*rgba)

    def pack(self, stream: BinaryIO) -> int:
        if not self.is_valid:
            raise ValueError(self)
        with StructIO(stream) as writer:
            return writer.pack("4f", (self.r, self.g, self.b, self.a))


Quaternion = Vector4
Rotator = Vector3


@dataclass
class Structure:
    type: str

    @classmethod
    def unpack_as_type(cls, stream: BinaryIO, build_version: int, type: str) -> 'Structure':
        unpacker = _unpack_map.get(type, DynamicStructure.unpack)
        structure = unpacker(stream, build_version)
        structure.type = type
        return structure


@dataclass
class DynamicStructure(Structure):
    properties: List[Property]

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'DynamicStructure':
        from satisfactory.properties import Property
        # None property used as terminal?
        properties = []
        while True:
            property = Property.unpack(stream, build_version)
            if not property:
                break
            else:
                properties.append(property)

        return DynamicStructure(None, properties)


@dataclass
class BoxStructure(Structure):  # Probably an AABB (Axis-Aligned Bounding Box), unk could be enabled?
    min: Vector3
    max: Vector3
    unk: bytes

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'BoxStructure':
        from satisfactory.properties import Property
        # None property used as terminal?
        min = Vector3.unpack(stream)
        max = Vector3.unpack(stream)
        unk = stream.read(1)

        return BoxStructure(None, min, max, unk)

@dataclass
class FluidBoxStructure(Structure):
    unk: float

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'FluidBoxStructure':
        with StructIO(stream) as reader:
            unk = reader.unpack("f")
            return FluidBoxStructure(None, unk)

@dataclass
class GuidStructure(Structure):
    data: bytes

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'GuidStructure':
        data = stream.read(16)
        return GuidStructure(None,data)


_unpack_map: Dict[str, Callable] = {
    "Box": BoxStructure.unpack,
    # Confusing, I know; UnityDEV here
    #   color via 4 bytes is Color32
    #   color via 4 floats is Color
    "Color": Color32.unpack,
    "LinearColor": Color.unpack,
    "Quat":Quaternion.unpack,
    "Vector":Vector3.unpack,
    "Vector2D":Vector2.unpack,
    "Rotator":Rotator.unpack,

}
