from enum import Enum
from dataclasses import dataclass
from typing import BinaryIO, List, Callable, Dict

from structio import StructIO, UInt32
from satisfactory.structures import Structure, DynamicStructure


# PropertyInfo = namedtuple("PropertyInfo", ['name',])


class PropertyType(Enum):
    Array = "ArrayProperty"
    Float = "FloatProperty"
    Int = "IntProperty"
    Byte = "ByteProperty"
    Enum = "EnumProperty"
    Bool = "BoolProperty"
    String = "StrProperty"
    Name = "NameProperty"
    Object = "ObjectProperty"
    Struct = "StructProperty"
    Map = "MapProperty"
    Text = "TextProperty"
    Set = "SetProperty"
    Int64 = "Int64Property"
    Int8 = "Int8Property"
    Interface = "InterfaceProperty"

    @classmethod
    def parse(cls, value: str) -> 'PropertyType':
        return PropertyType(value)  # previously was complicated before i forgot this; can propbably be 'un'factored


str_NONE = "None"


@dataclass
class Property:
    name: str
    type: PropertyType
    size: int
    index: int

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'Property':
        # Enforce null terminated for this particular run regardless of previous settings
        with StructIO(stream, str_null_terminated=True) as reader:
            name = reader.unpack_len_encoded_str()
            if name == str_NONE:
                return None
            type = reader.unpack_len_encoded_str()
            parsed_type = PropertyType.parse(type)
            size, index = reader.unpack("2I")
            unpacker = _unpack_map.get(parsed_type)
            if not unpacker:
                raise NotImplementedError(parsed_type)
            else:
                property = unpacker(stream, build_version)

                property.name = name
                property.type = type
                property.index = index
                property.size = size

                return property


@dataclass
class FloatProperty(Property):
    unk_flag: bytes
    value: float

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'FloatProperty':
        with StructIO(stream) as reader:
            flag, value = reader.unpack("=c f")
            return FloatProperty(None, None, None, None, flag, value)


@dataclass
class IntProperty(Property):
    unk_flag: bytes
    value: int

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'IntProperty':
        with StructIO(stream) as reader:
            flag, value = reader.unpack("=c i")
            return IntProperty(None, None, None, None, flag, value)


@dataclass
class StructProperty(Property):
    unks: bytes
    structure: Structure

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'StructProperty':
        with StructIO(stream, str_null_terminated=True) as reader:
            sub_type = reader.unpack_len_encoded_str()
            unks = reader.read(4 * 4 + 1)
            structure = Structure.unpack_as_type(stream, build_version, sub_type)
            return StructProperty(None, None, None, None, unks, structure)


@dataclass
class NameProperty(Property):
    unks: bytes
    value: str

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'StructProperty':
        with StructIO(stream, str_null_terminated=True) as reader:
            unks = reader.read(1)
            name = reader.unpack_len_encoded_str()
            return StructProperty(None, None, None, None, unks, name)


_unpack_map: Dict[PropertyType, Callable[[BinaryIO, int], Property]] = {
    PropertyType.Int: IntProperty.unpack,
    PropertyType.Float: FloatProperty.unpack,
    PropertyType.Struct: StructProperty.unpack,
    PropertyType.Name: NameProperty.unpack
}


@dataclass
class WorldObjectProperties:
    len: int
    unk: bytes
    properties: List[Property]

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'WorldObjectProperties':
        # Enforce null terminated for this particular run regardless of previous settings
        with StructIO(stream) as reader:
            now = reader.tell()
            size = reader.unpack(UInt32)
            unk = reader.read(12)
            properties = []
            while True:
                prop = Property.unpack(stream, build_version)
                if prop:
                    properties.append(prop)
                else:
                    break
            then = reader.tell()
            assert now + size == then, (now + size, then, then - (now + size))
        return WorldObjectProperties(size, unk, properties)
