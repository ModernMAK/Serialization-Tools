import enum
from collections import namedtuple
from dataclasses import dataclass
from typing import BinaryIO, List, ForwardRef, Callable, Dict, Tuple

from main import StructIO, UInt32


# PropertyInfo = namedtuple("PropertyInfo", ['name',])


@enum
class PropertyType:
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
        if value in cls.__members__:
            return cls.__members__[value]
        else:
            raise KeyError(value)


Property = ForwardRef("Property")


@dataclass
class ArrayProperty(Property):
    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'ArrayProperty':
        with StructIO(stream) as reader:
        sub_type =  
        raise NotImplementedError


@dataclass
class FloatProperty(Property):
    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'FloatProperty':
        raise NotImplementedError


@dataclass
class IntProperty(Property):
    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'IntProperty':
        raise NotImplementedError


@dataclass
class ByteProperty(Property):
    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'ByteProperty':
        raise NotImplementedError


@dataclass
class EnumProperty(Property):
    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'EnumProperty':
        raise NotImplementedError


@dataclass
class BoolProperty(Property):
    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'BoolProperty':
        raise NotImplementedError


@dataclass
class StringProperty(Property):
    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'StringProperty':
        raise NotImplementedError


_unpack_map: Dict[PropertyType, Callable[[BinaryIO, int], Property]] = {
    PropertyType.Int: IntProperty.unpack
}


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
            name, type = [reader.unpack_len_encoded_str() for _ in range(2)]
            parsed_type = PropertyType.parse(type)
            size, index = reader.unpack("2I")
            unpacker = _unpack_map.get(parsed_type)
            if not unpacker:
                raise NotImplementedError
            else:
                property = unpacker(stream,build_version,size)
                property.name = name
                property.type = type
                property.index = index
                property.size = size

@dataclass
class WorldObjectProperties:
    properties: List[Property]

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'WorldObjectProperties':
        # Enforce null terminated for this particular run regardless of previous settings
        with StructIO(stream) as reader:
            len = reader.unpack(UInt32)
            now = reader.tell()
            properties = []
            while reader.tell() < now + len:
                prop = Property.unpack(stream, build_version)
                properties.append(prop)
            then = reader.tell()
            assert now + len == then
        return WorldObjectProperties(properties)
