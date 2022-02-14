from dataclasses import dataclass
from enum import Enum
from typing import BinaryIO, List, Callable, Dict, Tuple, Any, Union, ClassVar, Optional

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

    def __repr__(self):
        return self.value


@dataclass
class PropertyData:
    pass


@dataclass
class PropertySubHeader:
    pass


@dataclass(unsafe_hash=True)
class PropertyHeader:
    name: str
    property_type: PropertyType
    index: int
    size: int

    NAME_LAYOUT = VStruct("v")
    HEADER_LAYOUT = VStruct("v2I")  # Not present for None properties.
    NONE_PROPERTY_NAME = "None"

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'PropertyHeader':
        name = cls.NAME_LAYOUT.unpack_stream(stream)[0]
        name = buffer_to_str(name)
        if name == cls.NONE_PROPERTY_NAME:
            raise NonePropertyError
        property_type, size, index = cls.HEADER_LAYOUT.unpack_stream(stream)
        property_type = PropertyType(buffer_to_str(property_type))
        return PropertyHeader(name, property_type, index, size)


class PropertyWindow(BinaryWindow):
    def __init__(self, stream: BinaryIO, header: PropertyHeader, assert_eos: bool = True):
        # READ FLAG
        buffer_start_byte = stream.read(1)
        assert buffer_start_byte == NULL
        # CREATE
        start = stream.tell()
        end = start + header.size
        super().__init__(stream, start, end)
        self._assert_eos = assert_eos

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            raise
        else:
            if self._assert_eos:
                assert end_of_stream(self)


@dataclass(unsafe_hash=True)
class Property:
    header: PropertyHeader
    sub_header: Optional[PropertySubHeader]
    data: Union[PropertyData, Any]

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'Property':
        if isinstance(stream, BinaryWindow):
            start = stream.abs_tell()  # Exclusively for Error raising purposes
        else:
            start = stream.tell()
        header = PropertyHeader.unpack(stream)

        generic_unpacker = _unpack_map.get(header.property_type)
        subheader_unpacker = _unpack_header_map.get(header.property_type)
        data_unpacker = _unpack_data_map.get(header.property_type)

        if not generic_unpacker and (not data_unpacker or not subheader_unpacker):
            raise NotImplementedError("Cant unpack property of type:", header.property_type.value, "@", as_hex_adr(start), "No unpacker was available!")

        if generic_unpacker:
            subheader = None
            with PropertyWindow(stream, header) as window:
                data = generic_unpacker(window)
        else:
            subheader = subheader_unpacker(stream)
            with PropertyWindow(stream, header) as window:
                data = data_unpacker(window, subheader)

        return Property(header, subheader, data)


_unpack_map: Dict[PropertyType, Callable[[BinaryIO], PropertyData]] = {}  # Does not require header

_unpack_header_map: Dict[PropertyType, Callable[[BinaryIO], PropertySubHeader]] = {}  # Unpack header
_unpack_data_map: Dict[PropertyType, Callable[[BinaryIO, PropertySubHeader], PropertyData]] = {}  # Requires data

_unpack_element_map: Dict[PropertyType, Callable[[BinaryIO], Any]] = {}  # Unpack element, (doesn't need header)
_unpack_array_map: Dict[PropertyType, Callable[[BinaryIO, int], List]] = {}  # Unpack array, (doesn't need header)


def __append_type_to_unpack(cls, prop_type):
    if hasattr(cls, "unpack_data"):
        _unpack_data_map[prop_type] = cls.unpack_data
    if hasattr(cls, "unpack_header"):
        _unpack_header_map[prop_type] = cls.unpack_header
    if hasattr(cls, "unpack_element"):
        _unpack_element_map[prop_type] = cls.unpack_element
    if hasattr(cls, "unpack_array"):
        _unpack_array_map[prop_type] = cls.unpack_array

    if hasattr(cls, "unpack"):
        if issubclass(cls, PropertySubHeader):
            _unpack_header_map[prop_type] = cls.unpack
        elif issubclass(cls, PropertyData):
            _unpack_map[prop_type] = cls.unpack
        else:
            raise NotImplementedError


@dataclass(unsafe_hash=True)
class NativePropertyData(PropertyData):
    LAYOUT: ClassVar[Struct] = None
    value: Any

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'NativePropertyData':
        value = cls.LAYOUT.unpack_stream(stream)[0]
        if hasattr(cls, "convert"):
            value = cls.convert(value)
        return cls(value)

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> Any:  # Here exclusively to support usage in map, should always prefer array
        value = arg = cls.LAYOUT.unpack_stream(stream)[0]
        if hasattr(cls, "convert"):
            value = cls.convert(arg)
        return value

    @classmethod
    def unpack_array(cls, stream: BinaryIO, count: int) -> List[Any]:
        value = list(structx.unpack_stream(f"{count}{cls.LAYOUT.format}", stream))
        if hasattr(cls, "convert"):
            value = [cls.convert(v) for v in value]
        return value


@dataclass(unsafe_hash=True)
class StringPropertyData(NativePropertyData):
    LAYOUT = VStruct("v")
    value: str

    @classmethod
    def convert(cls, v: Any) -> Any:
        return buffer_to_str(v)


@dataclass(unsafe_hash=True)
class IntPropertyData(NativePropertyData):
    LAYOUT = Struct("i")
    value: int


@dataclass(unsafe_hash=True)
class Int64PropertyData(NativePropertyData):
    LAYOUT = Struct("q")
    value: int


@dataclass(unsafe_hash=True)
class FloatPropertyData(NativePropertyData):
    LAYOUT = Struct("f")
    value: float


@dataclass
class RootPathPair:
    LAYOUT = VStruct("2v")
    root: str
    path: str

    @classmethod
    def unpack(cls, stream: BinaryIO) -> Tuple[str, str]:
        root, path = cls.LAYOUT.unpack_stream(stream)
        root, path = buffer_to_str(root), buffer_to_str(path)
        return root, path


@dataclass(unsafe_hash=True)
class ObjectPropertyData(PropertyData, RootPathPair):
    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'ObjectPropertyData':
        args = RootPathPair.unpack(stream)
        return ObjectPropertyData(*args)

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> 'ObjectPropertyData':
        return cls.unpack(stream)


@dataclass(unsafe_hash=True)
class ByteHeader(PropertySubHeader):
    LAYOUT = VStruct("v")
    byte_type: str

    @classmethod
    def unpack_header(cls, stream: BinaryIO) -> 'ByteHeader':
        type = buffer_to_str(cls.LAYOUT.unpack_stream(stream)[0])
        return ByteHeader(type)


# @dataclass(unsafe_hash=True)
class ByteProperty:
    LAYOUT = VStruct("v")

    # value: Union[bytes, str]

    @classmethod
    def unpack_data(cls, stream: BinaryIO, header: ByteHeader) -> Union[str, bytes]:
        if header.byte_type == PropertyHeader.NONE_PROPERTY_NAME:
            return stream.read(1)
        else:
            return buffer_to_str(cls.LAYOUT.unpack_stream(stream)[0])

    @classmethod
    def unpack_array(cls, stream: BinaryIO, count: int) -> bytes:
        return stream.read(count)


# @dataclass(unsafe_hash=True)
class BoolProperty:  # Bool is actually a 'header' in my implementation, flag comes after, wierd, IK
    LAYOUT = VStruct("?")

    # value: bool

    @classmethod
    def unpack_header(cls, stream: BinaryIO):
        return cls.LAYOUT.unpack_stream(stream)[0]

    @classmethod
    def unpack_data(cls, stream: BinaryIO, header: bool) -> None:
        return None


@dataclass(unsafe_hash=True)
class StructHeader(PropertySubHeader):
    LAYOUT = VStruct("v4I")
    struct_type: str
    abcd: Tuple[int, int, int, int]

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'StructHeader':
        type, a, b, c, d = cls.LAYOUT.unpack_stream(stream)
        return StructHeader(buffer_to_str(type), (a, b, c, d))


class StructProperty:
    @classmethod
    def unpack_data(cls, stream: BinaryIO, subheader: StructHeader) -> 'Structure':
        return Structure.unpack_as_type(stream, subheader.struct_type)

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> 'Structure':
        return DynamicStructure.unpack(stream)

    @classmethod
    def unpack_array(cls, stream: BinaryIO, count: int) -> List[Property]:
        raise NotImplementedError("Please use StructArrayProperty instead!")


@dataclass(unsafe_hash=True)
class NameProperty(StringPropertyData):
    pass


@dataclass(unsafe_hash=True)
class ArrayHeader(PropertySubHeader):
    LAYOUT = VStruct("v")
    array_type: PropertyType

    @classmethod
    def unpack(cls, stream: BinaryIO):
        array_type = cls.LAYOUT.unpack_stream(stream)[0]
        array_type = PropertyType(buffer_to_str(array_type))
        return ArrayHeader(array_type)


class ArrayProperty:
    LENGTH = VStruct("I")

    @classmethod
    def unpack_data(cls, stream: BinaryIO, header: ArrayHeader) -> Union[List, 'ArrayProperty']:
        count = cls.LENGTH.unpack_stream(stream)[0]
        if header.array_type == PropertyType.Struct:
            return StructArrayProperty.unpack_struct_array(stream, count)

        array_unpacker = _unpack_array_map.get(header.array_type)
        element_unpacker = _unpack_element_map.get(header.array_type)
        if array_unpacker:
            items = array_unpacker(stream, count)
        elif element_unpacker:
            items = [element_unpacker(stream) for _ in range(count)]
        else:
            raise NotImplementedError("Cant unpack array of type", header.array_type)
        return items


@dataclass
class StructArrayHeader(StructHeader):
    inner_property_header: PropertyHeader

    @classmethod
    def unpack_header(cls, stream: BinaryIO) -> 'StructArrayHeader':
        header = PropertyHeader.unpack(stream)
        assert header.name != PropertyHeader.NONE_PROPERTY_NAME, header.name
        assert header.property_type == PropertyType.Struct, header.property_type

        struct_header = StructHeader.unpack(stream)

        return StructArrayHeader(struct_header.struct_type, struct_header.abcd, header)


@dataclass(unsafe_hash=True)
class StructArrayProperty(ArrayProperty):
    struct_header: StructArrayHeader
    values: List[Structure]

    @classmethod
    def unpack_struct_array(cls, stream: BinaryIO, count: int) -> 'StructArrayProperty':
        sub_header = StructArrayHeader.unpack_header(stream)
        with PropertyWindow(stream, sub_header.inner_property_header) as window:
            items = []
            for i in range(count):
                structure = Structure.unpack_as_type(window, sub_header.struct_type)
                items.append(structure)

            return StructArrayProperty(sub_header, items)


@dataclass(unsafe_hash=True)
class MapHeader(PropertySubHeader):
    LAYOUT = VStruct("2v")

    key_type: PropertyType
    value_type: PropertyType

    @classmethod
    def unpack_header(cls, stream: BinaryIO) -> 'MapHeader':
        key_type, value_type = cls.LAYOUT.unpack_stream(stream)
        key_type = PropertyType(buffer_to_str(key_type))
        value_type = PropertyType(buffer_to_str(value_type))
        return MapHeader(key_type, value_type)


class MapProperty(PropertyData):
    LAYOUT = VStruct("2I")
    map: Dict[PropertyData, PropertyData]

    @classmethod
    def unpack_data(cls, stream: BinaryIO, header: MapHeader) -> dict:
        unk, count = cls.LAYOUT.unpack_stream(stream)
        assert unk == 0, unk

        key_unpacker = _unpack_element_map[header.key_type]
        value_unpacker = _unpack_element_map[header.value_type]

        key_value_map = {}
        for _ in range(count):
            key = key_unpacker(stream)
            value = value_unpacker(stream)
            key_value_map[key] = value

        return key_value_map


@dataclass(unsafe_hash=True)
class EnumHeader(PropertySubHeader):
    TYPE_LAYOUT = VStruct("v")
    enum_type: str

    @classmethod
    def unpack_header(cls, stream: BinaryIO) -> 'EnumHeader':
        sub_type = cls.TYPE_LAYOUT.unpack_stream(stream)[0]
        return EnumHeader(buffer_to_str(sub_type))


@dataclass(unsafe_hash=True)
class EnumProperty(PropertyData):
    WORD_LAYOUT = VStruct("v")
    enum_name: str

    @classmethod
    def unpack_data(cls, stream: BinaryIO, header: EnumHeader) -> 'EnumProperty':
        # We only need header to reconstruct enums, but thats outside the scope of this program
        # still, we need to include it in the definition to avoid using generic unpack
        name = cls.WORD_LAYOUT.unpack_stream(stream)[0]
        return EnumProperty(buffer_to_str(name))


@dataclass
class InterfaceProperty(PropertyData):
    LAYOUT = VStruct("2v")
    a: str
    b: str

    @classmethod
    def unpack(cls, stream: BinaryIO):
        a, b = cls.LAYOUT.unpack_stream(stream)
        return InterfaceProperty(buffer_to_str(a), buffer_to_str(b))

    @classmethod
    def unpack_element(cls, stream: BinaryIO):
        return cls.unpack(stream)


class WorldObjectProperties:
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
            # , (window.tell(), window.read()) # We dont check here because of excess data
            return properties


property2class = {
    PropertyType.Struct: [StructProperty, StructHeader],
    PropertyType.Bool: BoolProperty,
    PropertyType.String: StringPropertyData,
    PropertyType.Float: FloatPropertyData,
    PropertyType.Int64: Int64PropertyData,
    PropertyType.Int: IntPropertyData,
    PropertyType.Enum: [EnumHeader, EnumProperty],
    PropertyType.Byte: [ByteHeader, ByteProperty],
    PropertyType.Map: [MapHeader, MapProperty],
    PropertyType.Object: ObjectPropertyData,
    PropertyType.Array: [ArrayHeader, ArrayProperty],
    PropertyType.Name: NameProperty,
    # PropertyType.Int8: Int8Property,
    PropertyType.Interface: InterfaceProperty,
}
for key, prop in property2class.items():
    if isinstance(prop, list):
        for p in prop:
            __append_type_to_unpack(p, key)
    else:
        __append_type_to_unpack(prop, key)
