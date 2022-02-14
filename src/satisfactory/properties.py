from dataclasses import dataclass
from enum import Enum
from typing import BinaryIO, List, Callable, Dict, Tuple, Optional, Any, Union

from StructIO import structx
from StructIO.structio import as_hex_adr, BinaryWindow, end_of_stream
from StructIO.structx import Struct
from StructIO.vstruct import VStruct
from .shared import NonePropertyError, buffer_to_str
from .structures import Structure, DynamicStructure

NULL = b"\x00"


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


@dataclass
class PropertyData:
    pass


@dataclass(unsafe_hash=True)
class PropertyHeader:
    name: str
    property_type: PropertyType
    index: int
    """ The size of the property when it was read """
    read_size: int

    NAME_LAYOUT = VStruct("v")
    HEADER_LAYOUT = VStruct("v2I")  # Not present for None properties.
    NONE_PROPERTY_NAME = "None"

    @classmethod
    def unpack(cls, stream: BinaryIO) -> Optional['PropertyHeader']:
        name: str = buffer_to_str(cls.NAME_LAYOUT.unpack_stream(stream)[0])
        if name == cls.NONE_PROPERTY_NAME:
            raise NonePropertyError
        property_type, size, index = cls.HEADER_LAYOUT.unpack_stream(stream)
        property_type = PropertyType(buffer_to_str(property_type))
        return PropertyHeader(name, property_type, index, size)


# This performs the validation check for the buffer start byte (0x00) and excludes it from reads
def create_property_window(stream: BinaryIO, header: PropertyHeader) -> BinaryWindow:
    buffer_start_byte = stream.read(1)
    assert buffer_start_byte == b'\x00'
    return BinaryWindow.slice(stream, header.read_size)


@dataclass(unsafe_hash=True)
class Property:
    header: PropertyHeader
    data: PropertyData

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'Property':
        header = PropertyHeader.unpack(stream)
        data_unpacker = _unpack_map.get(header.property_type)
        if not data_unpacker:
            raise NotImplementedError("Cant unpack property of type:", header.property_type.value, "@", as_hex_adr(stream.tell()))
        data = data_unpacker(stream, header)
        return Property(header, data)


_unpack_map: Dict[PropertyType, Callable[[BinaryIO, PropertyHeader], PropertyData]] = {}
_unpack_element_map: Dict[PropertyType, Callable[[BinaryIO], PropertyData]] = {}
_unpack_array_map: Dict[PropertyType, Callable[[BinaryIO, int], List[PropertyData]]] = {}


@dataclass(unsafe_hash=True)
class NativeTypePropertyData(PropertyData):
    value: Any

    @classmethod
    def unpack(cls, stream: BinaryIO, header: PropertyHeader) -> 'NativeTypePropertyData':
        raise NotImplementedError

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> Any:
        raise NotImplementedError

    @classmethod
    def unpack_array(cls, stream: BinaryIO, count: int) -> Any:
        raise NotImplementedError


def __append_type_to_unpack(cls, prop_type):
    if hasattr(cls, "unpack"):
        _unpack_map[prop_type] = cls.unpack
    if hasattr(cls, "unpack_element"):
        _unpack_element_map[prop_type] = cls.unpack_element
    if hasattr(cls, "unpack_array"):
        _unpack_array_map[prop_type] = cls.unpack_array


@dataclass(unsafe_hash=True)
class StringPropertyData(PropertyData):
    LAYOUT = VStruct("v")
    name: str

    @classmethod
    def unpack(cls, stream: BinaryIO, header: PropertyHeader) -> 'StringPropertyData':
        with create_property_window(stream, header) as window:
            value = cls.LAYOUT.unpack_stream(window)[0]
            assert end_of_stream(window)
            return StringPropertyData(buffer_to_str(value))


@dataclass(unsafe_hash=True)
class IntPropertyData(NativeTypePropertyData):
    LAYOUT = Struct("i")
    value: int

    @classmethod
    def unpack(cls, stream: BinaryIO, header: PropertyHeader) -> 'IntPropertyData':
        with create_property_window(stream, header) as window:
            value = cls.LAYOUT.unpack_stream(window)[0]
            assert end_of_stream(window)
            return IntPropertyData(value)

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> int:
        return cls.LAYOUT.unpack_stream(stream)[0]

    @classmethod
    def unpack_array(cls, stream: BinaryIO, count: int) -> List[int]:
        return list(structx.unpack_stream(f"{count}i", stream))


@dataclass(unsafe_hash=True)
class Int64PropertyData(PropertyData):
    LAYOUT = Struct("q")
    value: int

    @classmethod
    def unpack(cls, stream: BinaryIO, header: PropertyHeader) -> 'Int64PropertyData':
        with create_property_window(stream, header) as window:
            value = cls.LAYOUT.unpack_stream(window)[0]
            assert end_of_stream(window)
            return Int64PropertyData(value)

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> int:
        return cls.LAYOUT.unpack_stream(stream)[0]

    @classmethod
    def unpack_array(cls, stream: BinaryIO, count: int) -> List[int]:
        return list(structx.unpack_stream(f"{count}I", stream))


@dataclass(unsafe_hash=True)
class FloatPropertyData(NativeTypePropertyData):
    LAYOUT = Struct("f")
    value: float

    @classmethod
    def unpack(cls, stream: BinaryIO, header: PropertyHeader) -> 'FloatPropertyData':
        with create_property_window(stream, header) as window:
            value = cls.LAYOUT.unpack_stream(window)[0]
            assert end_of_stream(window)
            return FloatPropertyData(value)

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> float:
        return cls.LAYOUT.unpack_stream(stream)[0]

    @classmethod
    def unpack_array(cls, stream: BinaryIO, count: int) -> List[float]:
        return list(structx.unpack_stream(f"{count}f", stream))


@dataclass(unsafe_hash=True)
class ObjectPropertyData(PropertyData):
    LAYOUT = VStruct("2v")

    level: str
    path: str

    @classmethod
    def unpack(cls, stream: BinaryIO, header: PropertyHeader) -> 'ObjectPropertyData':
        with create_property_window(stream, header) as window:
            r = cls.unpack_element(window)
            assert end_of_stream(window)
            return r

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> 'ObjectPropertyData':
        level, path = cls.LAYOUT.unpack_stream(stream)
        return ObjectPropertyData(buffer_to_str(level), buffer_to_str(path))


@dataclass(unsafe_hash=True)
class ByteProperty(PropertyData):
    TYPE_LAYOUT = VStruct("v")
    WORD_LAYOUT = VStruct("v")
    byte_type: str
    value: Union[bytes, str]

    @classmethod
    def unpack(cls, stream: BinaryIO, header: PropertyHeader) -> 'ByteProperty':
        sub_type = buffer_to_str(cls.TYPE_LAYOUT.unpack_stream(stream)[0])
        with create_property_window(stream, header) as window:
            if sub_type == PropertyHeader.NONE_PROPERTY_NAME:
                value = stream.read(1)
            else:
                value = buffer_to_str(cls.WORD_LAYOUT.unpack_stream(window)[0])
            assert end_of_stream(window)
            return ByteProperty(sub_type, value)

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> bytes:
        raise NotImplementedError("Byte property should be read by element!")

    @classmethod
    def unpack_array(cls, stream: BinaryIO, count: int) -> bytes:
        return stream.read(count)


@dataclass(unsafe_hash=True)
class BoolProperty(PropertyData):
    internal_value: bytes

    @property
    def as_bool(self) -> bool:
        return self.internal_value[0] > 0

    @property
    def as_int(self) -> int:
        return int(self.internal_value[0])

    @classmethod
    def unpack(cls, stream: BinaryIO, header: PropertyHeader) -> 'BoolProperty':
        assert header.read_size == 0
        value, flag = stream.read(2)
        assert flag == 0, flag
        return BoolProperty(value)

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> bytes:
        return stream.read(1)

    @classmethod
    def unpack_array(cls, stream: BinaryIO, count: int) -> bytes:
        return stream.read(count)


@dataclass(unsafe_hash=True)
class StructProperty(PropertyData):
    LAYOUT = VStruct("v4I")
    abcd: Tuple[int, int, int, int]
    structure: Structure

    @classmethod
    def unpack(cls, stream: BinaryIO, header: PropertyHeader) -> 'StructProperty':
        sub_type, a, b, c, d = cls.LAYOUT.unpack_stream(stream)
        with create_property_window(stream, header) as window:
            structure = Structure.unpack_as_type(window, buffer_to_str(sub_type))
            assert end_of_stream(window)
            return StructProperty((a, b, c, d), structure)

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> 'Structure':
        return DynamicStructure.unpack(stream)

    @classmethod
    def unpack_array(cls, stream: BinaryIO, count: int) -> List[Property]:
        raise NotImplementedError("Please use StructArrayProperty instead!")


@dataclass(unsafe_hash=True)
class NameProperty(PropertyData):
    LAYOUT = VStruct("v")
    name: str

    @classmethod
    def unpack(cls, stream: BinaryIO, header: PropertyHeader) -> 'NameProperty':
        with create_property_window(stream, header) as window:
            name = buffer_to_str(cls.LAYOUT.unpack_stream(window)[0])
            assert end_of_stream(window)
            return NameProperty(name)


@dataclass(unsafe_hash=True)
class ArrayProperty(PropertyData):
    HEADER = VStruct("v")
    LENGTH = VStruct("I")
    array_type: PropertyType
    values: List


    @classmethod
    def unpack(cls, stream: BinaryIO, header: PropertyHeader) -> 'ArrayProperty':
        array_type = cls.HEADER.unpack_stream(stream)[0]
        array_type = PropertyType(buffer_to_str(array_type))
        with create_property_window(stream, header) as window:
            count = cls.LENGTH.unpack_stream(window)[0]
            if array_type == PropertyType.Struct:  # Struct plays by its own rules
                r = StructArrayProperty.unpack_struct_array(window, count, array_type)
                assert end_of_stream(window)
                return r
            else:
                array_unpacker = _unpack_array_map.get(array_type)
                element_unpacker = _unpack_element_map.get(array_type)
                if array_unpacker:
                    items = array_unpacker(window, count)
                elif element_unpacker:
                    items = [element_unpacker(window) for _ in range(count)]
                else:
                    raise NotImplementedError("Cant unpack array of type", array_type)
                assert end_of_stream(window)
                return ArrayProperty(array_type, items)


@dataclass(unsafe_hash=True)
class StructArrayProperty(ArrayProperty):
    array_type: PropertyType
    sub_header: PropertyHeader
    abcd: Tuple[int, int, int, int]
    values: List[Structure]
    __structure_type: str  # Present for ease of use


    @classmethod
    def unpack_struct_array(cls, stream: BinaryIO, count: int, array_type: PropertyType) -> 'StructArrayProperty':
        header = PropertyHeader.unpack(stream)
        assert header.name != PropertyHeader.NONE_PROPERTY_NAME, header.name
        assert header.property_type == PropertyType.Struct, header.property_type

        struct_type, a, b, c, d = StructProperty.LAYOUT.unpack_stream(stream)
        struct_type = buffer_to_str(struct_type)
        items = []
        abcd = (a, b, c, d)
        with create_property_window(stream, header) as window:
            for i in range(count):
                structure = Structure.unpack_as_type(window, struct_type)
                items.append(structure)
            assert end_of_stream(window)
            return StructArrayProperty(array_type, items, header, abcd, struct_type)


@dataclass(unsafe_hash=True)
class MapProperty(PropertyData):
    LAYOUT = VStruct("2v")
    INNER_LAYOUT = VStruct("2I")
    key_type: PropertyType
    value_type: PropertyType
    map: Dict[PropertyData, PropertyData]

    @classmethod
    def unpack(cls, stream: BinaryIO, header: PropertyHeader) -> 'MapProperty':
        key_type, value_type = cls.LAYOUT.unpack_stream(stream)
        with create_property_window(stream, header) as window:
            unk, count = cls.INNER_LAYOUT.unpack_stream(window)
            assert unk == 0, unk

            key_type = PropertyType(buffer_to_str(key_type))
            value_type = PropertyType(buffer_to_str(value_type))

            key_unpacker = _unpack_element_map[key_type]
            value_unpacker = _unpack_element_map[value_type]

            key_value_map = {}
            for _ in range(count):
                key = key_unpacker(stream)
                value = value_unpacker(stream)
                key_value_map[key] = value
            assert end_of_stream(window)
            return MapProperty(key_type, value_type, key_value_map)


@dataclass(unsafe_hash=True)
class EnumProperty(PropertyData):
    TYPE_LAYOUT = VStruct("v")
    WORD_LAYOUT = VStruct("v")
    enum_type: str
    enum_name: str

    @classmethod
    def unpack(cls, stream: BinaryIO, header: PropertyHeader) -> 'EnumProperty':
        sub_type = cls.TYPE_LAYOUT.unpack_stream(stream)[0]
        with create_property_window(stream, header) as window:
            name = cls.WORD_LAYOUT.unpack_stream(window)[0]
            assert end_of_stream(window)
            return EnumProperty(buffer_to_str(sub_type), buffer_to_str(name))


@dataclass
class InterfaceProperty:
    LAYOUT = VStruct("2v")
    a: str
    b: str

    @classmethod
    def unpack(cls, stream: BinaryIO, header: PropertyHeader):
        with create_property_window(stream, header) as window:
            a, b = cls.LAYOUT.unpack_stream(window)
            assert end_of_stream(window)
            return InterfaceProperty(buffer_to_str(a), buffer_to_str(b))

    @classmethod
    def unpack_element(cls, stream: BinaryIO):
        a, b = cls.LAYOUT.unpack_stream(stream)
        return InterfaceProperty(buffer_to_str(a), buffer_to_str(b))


class WorldObjectProperties:
    # properties: List[Property]
    # zero: int

    UInt32 = Struct("I")

    @classmethod
    def unpack(cls, stream: BinaryIO, size: int) -> List[Property]:
        with BinaryWindow.slice(stream, size) as window:
            properties = []
            while True:
                try:
                    prop = Property.unpack(window)
                    properties.append(prop)
                except NonePropertyError:
                    break
            zero = cls.UInt32.unpack_stream(window)[0]
            assert zero == 0, zero
            # assert end_of_stream(window), (window.tell(), window.read()) # We dont check here because of excess data
            return properties


property2class = {
    PropertyType.Struct: StructProperty,
    PropertyType.Bool: BoolProperty,
    PropertyType.String: StringPropertyData,
    PropertyType.Float: FloatPropertyData,
    PropertyType.Int64: Int64PropertyData,
    PropertyType.Int: IntPropertyData,
    PropertyType.Enum: EnumProperty,
    PropertyType.Byte: ByteProperty,
    PropertyType.Map: MapProperty,
    PropertyType.Object: ObjectPropertyData,
    PropertyType.Array: ArrayProperty,
    PropertyType.Name: NameProperty,
    # PropertyType.Int8: Int8Property,
    PropertyType.Interface: InterfaceProperty,
}
for key, name in property2class.items():
    __append_type_to_unpack(name, key)
