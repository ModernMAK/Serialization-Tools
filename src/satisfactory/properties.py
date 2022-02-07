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

    @classmethod
    def unpack_element(cls, stream: BinaryIO, build_version: int) -> 'Property':
        raise NotImplementedError


@dataclass
class FloatProperty(Property):
    unk_flag: bytes
    value: float

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'FloatProperty':
        with StructIO(stream) as reader:
            flag, value = reader.unpack("=c f")
            return FloatProperty(None, None, None, None, flag, value)

    @classmethod
    def unpack_element(cls, stream: BinaryIO, build_version: int) -> 'FloatProperty':
        raise NotImplementedError


@dataclass
class IntProperty(Property):
    unk_flag: bytes
    value: int

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'IntProperty':
        with StructIO(stream) as reader:
            flag, value = reader.unpack("=c i")
            return IntProperty(None, PropertyType.Int, None, None, flag, value)

    @classmethod
    def unpack_element(cls, stream: BinaryIO, build_version: int) -> 'IntProperty':
        with StructIO(stream) as reader:
            value = reader.unpack("i")
            return IntProperty(None, PropertyType.Int, None, None, None, value)


@dataclass
class StructProperty(Property):
    a: int
    b: int
    c: int
    d: int
    e: bytes
    structure: Structure

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'StructProperty':
        with StructIO(stream, str_null_terminated=True) as reader:
            sub_type = reader.unpack_len_encoded_str()
            a, b, c, d, e = reader.unpack("=4I c")
            structure = Structure.unpack_as_type(stream, build_version, sub_type)
            return StructProperty(None, None, None, None, a, b, c, d, e, structure)

    @classmethod
    def unpack_element(cls, stream: BinaryIO, build_version: int) -> 'StructProperty':
        raise NotImplementedError

    @classmethod
    def unpack_array(cls, stream: BinaryIO, build_version: int, count: int) -> 'List[StructProperty]':
        with StructIO(stream, str_null_terminated=True) as reader:
            name = reader.unpack_len_encoded_str()
            assert name != str_NONE

            type = reader.unpack_len_encoded_str()
            parsed_type = PropertyType.parse(type)
            assert parsed_type == PropertyType.Struct

            size, index = reader.unpack("2I")

            sub_type = reader.unpack_len_encoded_str()

            a, b, c, d, e = reader.unpack("=4I c")

            items = []
            for i in range(count):
                structure = Structure.unpack_as_type(stream, build_version, sub_type)
                prop = StructProperty(name, parsed_type, size, index, a, b, c, d, e, structure)
                items.append(prop)
            return items


@dataclass
class NameProperty(Property):
    unks: bytes
    value: str

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'NameProperty':
        with StructIO(stream, str_null_terminated=True) as reader:
            unks = reader.read(1)
            name = reader.unpack_len_encoded_str()
            return NameProperty(None, None, None, None, unks, name)

    @classmethod
    def unpack_element(cls, stream: BinaryIO, build_version: int) -> 'NameProperty':
        raise NotImplementedError


@dataclass
class ArrayProperty(Property):
    unks: bytes
    values: List

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int) -> 'ArrayProperty':
        with StructIO(stream, str_null_terminated=True) as reader:
            sub_type = reader.unpack_len_encoded_str()
            parsed_type = PropertyType.parse(sub_type)
            a = reader.unpack("c")
            count = reader.unpack("I")
            array_unpacker = _unpack_array_map.get(parsed_type)
            element_unpacker = _unpack_element_map.get(parsed_type)
            if array_unpacker:
                items = array_unpacker(stream, build_version, count)
            elif element_unpacker:
                items = []
                for i in range(count):
                    item = element_unpacker(stream, build_version)
                    item.name = f"Element {i}"
                    items.append(item)
            else:
                raise NotImplementedError

            return ArrayProperty(None, None, None, None, a, items)

    @classmethod
    def unpack_element(cls, stream: BinaryIO, build_version: int) -> 'ArrayProperty':
        raise NotImplementedError


_unpack_map: Dict[PropertyType, Callable[[BinaryIO, int], Property]] = {
    PropertyType.Int: IntProperty.unpack,
    PropertyType.Float: FloatProperty.unpack,
    PropertyType.Struct: StructProperty.unpack,
    PropertyType.Name: NameProperty.unpack,
    PropertyType.Array: ArrayProperty.unpack
}
_unpack_element_map: Dict[PropertyType, Callable[[BinaryIO, int], Property]] = {
    PropertyType.Int: IntProperty.unpack_element,
    PropertyType.Float: FloatProperty.unpack_element,
    PropertyType.Struct: StructProperty.unpack_element,
    PropertyType.Name: NameProperty.unpack_element,
    PropertyType.Array: ArrayProperty.unpack_element
}
_unpack_array_map: Dict[PropertyType, Callable[[BinaryIO, int, int], List[Property]]] = {
    PropertyType.Struct: StructProperty.unpack_array,
}


@dataclass
class WorldObjectProperties:
    properties: List[Property]
    zero: int

    @classmethod
    def unpack(cls, stream: BinaryIO, build_version: int, size: int = None) -> 'WorldObjectProperties':
        # Enforce null terminated for this particular run regardless of previous settings
        with StructIO(stream) as reader:
            if not size:
                read_size = size = reader.unpack("I")
            bm = reader.tell()
            properties = []
            while True:
                prop = Property.unpack(stream, build_version)
                if prop:
                    properties.append(prop)
                else:
                    break
            zero = reader.unpack("I")
            assert bm + size == stream.tell(), (bm, size, stream.tell(), stream.tell() - (bm + size))
        return WorldObjectProperties(properties, zero)
