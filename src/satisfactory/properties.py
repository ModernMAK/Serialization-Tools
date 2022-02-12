from dataclasses import dataclass
from enum import Enum
from typing import BinaryIO, List, Callable, Dict, Tuple, Optional, Any, Union

from StructIO import structx
from StructIO.structio import as_hex_adr
from StructIO.structx import Struct
from StructIO.vstruct import VStruct
from satisfactory.error import NonePropertyError
from satisfactory.structures import Structure, DynamicStructure

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
    @property
    def excess_read_size(self) -> int:
        """
            Size read that excludes the 'data' portion of a property.
            E.G. A Dynamic Structure with only the None property present should only contain 9 bytes
                Due to the nature of Dynamic Structure; an additional amount of bytes are read for the name and type, despite note being part of the data size
        """
        return 0


@dataclass(unsafe_hash=True)
class PropertyHeader:
    name: str
    property_type: PropertyType
    index: int
    """ The size of the property when it was read """
    read_size: int

    NAME_LAYOUT = VStruct("v")
    HEADER_LAYOUT = VStruct("v2I")  # Not present for None properties.
    NONE_PROPERTY_NAME = "None\0"

    @classmethod
    def unpack(cls, stream: BinaryIO) -> Optional['PropertyHeader']:
        name: str = cls.NAME_LAYOUT.unpack_stream(stream)[0].decode()
        if name == cls.NONE_PROPERTY_NAME:
            raise NonePropertyError
        property_type, size, index = cls.HEADER_LAYOUT.unpack_stream(stream)
        property_type = PropertyType(property_type.decode()[:-1])
        return PropertyHeader(name, property_type, index, size)


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

        before = stream.tell()
        data = data_unpacker(stream)
        after = stream.tell()
        delta = after - before
        expected = delta - data.excess_read_size
        required_excess = delta - header.read_size

        assert expected == header.read_size, (expected, header.read_size, " ", as_hex_adr(before), as_hex_adr(after), " ", data.excess_read_size, "/", required_excess, " ", header.read_size - expected)
        return Property(header, data)


_unpack_map: Dict[PropertyType, Callable[[BinaryIO], PropertyData]] = {}
_unpack_element_map: Dict[PropertyType, Callable[[BinaryIO], PropertyData]] = {}
_unpack_array_map: Dict[PropertyType, Callable[[BinaryIO, int], List[PropertyData]]] = {}


@dataclass(unsafe_hash=True)
class NativeTypePropertyData(PropertyData):
    name: Any

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'NativeTypePropertyData':
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
    LAYOUT = VStruct("cv")
    name: str

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'StringPropertyData':
        flag, value = cls.LAYOUT.unpack_stream(stream)
        assert flag == NULL, flag
        return StringPropertyData(value.decode())


@dataclass(unsafe_hash=True)
class IntPropertyData(NativeTypePropertyData):
    LAYOUT = Struct("=ci")
    ELEM_LAYOUT = Struct("i")
    name: int

    @property
    def excess_read_size(self) -> int:
        return 1 # for flag

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'IntPropertyData':
        flag, value = cls.LAYOUT.unpack_stream(stream)
        assert flag == NULL, flag
        return IntPropertyData(value)

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> int:
        return cls.ELEM_LAYOUT.unpack_stream(stream)[0]

    @classmethod
    def unpack_array(cls, stream: BinaryIO, count: int) -> List[int]:
        return list(structx.unpack_stream(f"{count}i", stream))


@dataclass(unsafe_hash=True)
class Int64PropertyData(PropertyData):
    LAYOUT = Struct("=cI")
    ELEM_LAYOUT = Struct("I")
    name: int

    @property
    def excess_read_size(self) -> int:
        return 1 # for flag

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'Int64PropertyData':
        flag, value = cls.LAYOUT.unpack_stream(stream)
        assert flag == NULL, flag
        return Int64PropertyData(value)

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> int:
        return cls.ELEM_LAYOUT.unpack_stream(stream)[0]

    @classmethod
    def unpack_array(cls, stream: BinaryIO, count: int) -> List[int]:
        return list(structx.unpack_stream(f"{count}I", stream))


@dataclass(unsafe_hash=True)
class FloatPropertyData(NativeTypePropertyData):
    LAYOUT = Struct("=cf")
    ELEM_LAYOUT = Struct("f")
    name: float

    @property
    def excess_read_size(self) -> int:
        return 1 # for flag

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'FloatPropertyData':
        flag, value = cls.LAYOUT.unpack_stream(stream)
        assert flag == NULL, flag
        return FloatPropertyData(value)

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> float:
        return cls.ELEM_LAYOUT.unpack_stream(stream)[0]

    @classmethod
    def unpack_array(cls, stream: BinaryIO, count: int) -> List[float]:
        return list(structx.unpack_stream(f"{count}f", stream))


@dataclass(unsafe_hash=True)
class ObjectPropertyData(PropertyData):
    LAYOUT = VStruct("=c2v")
    ELEM_LAYOUT = VStruct("2v")

    level: str
    path: str

    @property
    def excess_read_size(self) -> int:
        return 1 # for flag

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'ObjectPropertyData':
        flag, level, path = cls.LAYOUT.unpack_stream(stream)
        assert flag == NULL, flag
        return ObjectPropertyData(level.decode(), path.decode())

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> 'ObjectPropertyData':
        level, path = cls.ELEM_LAYOUT.unpack_stream(stream)
        return ObjectPropertyData(level.decode(), path.decode())


@dataclass(unsafe_hash=True)
class ByteProperty(PropertyData):
    PREFIX_LAYOUT = VStruct("vc")
    WORD_LAYOUT = VStruct("v")
    byte_type: str
    name: Union[bytes, str]

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'ByteProperty':
        sub_type, flag = cls.PREFIX_LAYOUT.unpack_stream(stream)
        assert flag == NULL, flag
        if sub_type == PropertyHeader.NONE_PROPERTY_NAME:
            value = stream.read(1)
            return ByteProperty(sub_type, value)
        else:
            value = cls.WORD_LAYOUT.unpack_stream(stream)[0].decode()
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
    def excess_read_size(self) -> int:
        return 2 # for some reason read_size is 0; because this is a fixed size?

    @property
    def as_bool(self) -> bool:
        return self.internal_value[0] > 0

    @property
    def as_int(self) -> int:
        return int(self.internal_value[0])

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'BoolProperty':
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
    LAYOUT = VStruct("v=4Ic")
    abcd: Tuple[int, int, int, int]
    structure: Structure

    @property
    def excess_read_size(self) -> int:
        return self.LAYOUT.min_size + (len(self.structure.structure_type) + 1)

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'StructProperty':
        sub_type, a, b, c, d, flag = cls.LAYOUT.unpack_stream(stream)
        assert flag == NULL, flag
        structure = Structure.unpack_as_type(stream, sub_type.decode()[:-1])
        return StructProperty((a, b, c, d), structure)

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> 'Structure':
        return DynamicStructure.unpack(stream)

    @classmethod
    def unpack_array(cls, stream: BinaryIO, count: int) -> List[Property]:
        raise NotImplementedError("Please use StructArrayProperty instead!")


@dataclass(unsafe_hash=True)
class NameProperty(PropertyData):

    @property
    def excess_read_size(self) -> int:
        return 1  # Because the flag value I guess?

    LAYOUT = VStruct("cv")
    name: str

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'NameProperty':
        flag, name = cls.LAYOUT.unpack_stream(stream)
        assert flag == NULL, flag
        return NameProperty(name.decode())


@dataclass(unsafe_hash=True)
class ArrayProperty(PropertyData):
    HEADER = VStruct("v=cI")
    array_type: PropertyType
    values: List

    @property
    def excess_read_size(self) -> int:
        return 4 + len(self.array_type.value) + 1 + 1


    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'ArrayProperty':
        array_type, flag, count = cls.HEADER.unpack_stream(stream)
        array_type = PropertyType(array_type.decode()[:-1])
        assert flag == NULL, flag

        if array_type == PropertyType.Struct:  # Struct plays by its own rules
            return StructArrayProperty.unpack(stream, count, array_type)
        else:
            array_unpacker = _unpack_array_map.get(array_type)
            element_unpacker = _unpack_element_map.get(array_type)
            if array_unpacker:
                items = array_unpacker(stream, count)
            elif element_unpacker:
                items = [element_unpacker(stream) for _ in range(count)]
            else:
                raise NotImplementedError("Cant unpack array of type", array_type)

            return ArrayProperty(array_type, items)


@dataclass(unsafe_hash=True)
class StructArrayProperty(ArrayProperty):
    array_type: PropertyType
    sub_header: PropertyHeader
    abcd: Tuple[int, int, int, int]
    values: List[Structure]
    __structure_type: str  # Present for ease of use

    @property
    def excess_read_size(self) -> int:
        return 20 # Hardcoded for now, will fail eventually, TODO fix this

    @classmethod
    def unpack(cls, stream: BinaryIO, count: int, array_type: PropertyType) -> 'StructArrayProperty':
        header = PropertyHeader.unpack(stream)
        assert header.name != PropertyHeader.NONE_PROPERTY_NAME, header.name
        assert header.property_type == PropertyType.Struct, header.property_type

        struct_type, a, b, c, d, flag = StructProperty.LAYOUT.unpack_stream(stream)
        assert flag == NULL, flag
        struct_type = struct_type.decode()[:-1]

        items = []
        abcd = (a, b, c, d)

        before = stream.tell()
        for i in range(count):
            structure = Structure.unpack_as_type(stream, struct_type)
            items.append(structure)
        after = stream.tell()
        assert (after - before) == header.read_size, (after - before, header.read_size, after - before - header.read_size)
        return StructArrayProperty(array_type, items, header, abcd, struct_type)


@dataclass(unsafe_hash=True)
class MapProperty(PropertyData):
    LAYOUT = VStruct("2v=c2I")
    key_type: PropertyType
    value_type: PropertyType
    map: Dict[PropertyData, PropertyData]

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'MapProperty':
        key_type, value_type, flag, unk, count = cls.LAYOUT.unpack_stream(stream)
        key_type = PropertyType(key_type.decode()[:-1])
        value_type = PropertyType(value_type.decode()[:-1])

        key_unpacker = _unpack_element_map[key_type]
        value_unpacker = _unpack_element_map[value_type]

        assert flag == NULL, unk
        assert unk == 0, unk

        map = {}

        for _ in range(count):
            key = key_unpacker(stream)
            value = value_unpacker(stream)
            map[key] = value
        return MapProperty(key_type, value_type, map)


@dataclass(unsafe_hash=True)
class EnumProperty(PropertyData):
    LAYOUT = VStruct("vcv")
    enum_type: str
    enum_name: str

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'EnumProperty':
        sub_type, flag, name = cls.LAYOUT.unpack_stream(stream)
        assert flag == 0
        return EnumProperty(sub_type.decode(), name.decode())


@dataclass
class ExcessDataProperty(PropertyData):
    excess: bytes


class WorldObjectProperties:
    # properties: List[Property]
    # zero: int

    UInt32 = Struct("I")

    @classmethod
    def unpack(cls, stream: BinaryIO, size: int = None) -> Tuple[List[Property], int]:
        # Enforce null terminated for this particular run regardless of previous settings
        if not size:
            read_size = size = cls.UInt32.unpack(stream)
        bm = stream.tell()
        properties = []
        while True:
            try:
                prop = Property.unpack(stream)
                properties.append(prop)
            except NonePropertyError:
                break
        zero = cls.UInt32.unpack_stream(stream)[0]
        assert zero == 0, zero
        excess = (bm + size) - stream.tell()
        # excess_buffer = None
        if excess > 0:
            pass
        elif excess < 0:
            raise NotImplementedError("Read too much data!", excess)
        return properties, excess


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
    # PropertyType.Interface: InterfaceProperty,
}
for key, name in property2class.items():
    __append_type_to_unpack(name, key)
