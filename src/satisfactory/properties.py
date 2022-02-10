from enum import Enum
from dataclasses import dataclass
from typing import BinaryIO, List, Callable, Dict, Tuple

from StructIO.structio import StructIO, UInt32, as_hex_adr, Int32, Int64
from satisfactory.structures import Structure, DynamicStructure

# PropertyInfo = namedtuple("PropertyInfo", ['name',])

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

    @classmethod
    def parse(cls, value: str) -> 'PropertyType':
        return PropertyType(value)  # previously was complicated before I forgot this; can propbably be 'un'factored


str_NONE = "None"


@dataclass
class PropertyData:
    pass


@dataclass(unsafe_hash=True)
class Property:
    name: str
    type: PropertyType
    # size: int
    index: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'Property':
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
                raise NotImplementedError("Cant unpack property of type:", parsed_type, "@", as_hex_adr(stream.tell()))
            else:
                property = unpacker(stream)  # TODO pass in size for verification

                property.name = name
                property.type = type
                property.index = index
                # property.size = size

                return property


@dataclass(unsafe_hash=True)
class FloatProperty(Property):
    # unk_flag: bytes
    value: float

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'FloatProperty':
        with StructIO(stream) as reader:
            flag, value = reader.unpack("=c f")
            assert flag == NULL, flag
            return FloatProperty(None, None, None, value)


@dataclass(unsafe_hash=True)
class StringProperty(Property):
    # unk_flag: bytes
    value: str

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'StringProperty':
        with StructIO(stream) as reader:
            flag = reader.read(1)
            assert flag == NULL, flag
            value = reader.unpack_len_encoded_str()
            return StringProperty(None, PropertyType.String, None, value)


@dataclass(unsafe_hash=True)
class ObjectPropertyData(PropertyData):
    level: str
    path: str

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'ObjectPropertyData':
        with StructIO(stream) as reader:
            level = reader.unpack_len_encoded_str()
            path = reader.unpack_len_encoded_str()
            return ObjectPropertyData(level, path)


@dataclass(unsafe_hash=True)
class ObjectProperty(Property):
    data: ObjectPropertyData

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'ObjectProperty':
        flag = stream.read(1)
        assert flag == NULL, flag
        data = ObjectPropertyData.unpack(stream)
        return ObjectProperty(None, None, None, data)


@dataclass(unsafe_hash=True)
class ByteProperty(Property):
    value: bytes
    named_value: str

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'ByteProperty':
        with StructIO(stream) as reader:
            sub_type = reader.unpack_len_encoded_str()
            flag = reader.read(1)
            assert flag == NULL, flag
            if sub_type == "None":
                value = reader.read(1)
                return ByteProperty(None, None, None, value, None)
            else:
                value = reader.unpack_len_encoded_str()
                return ByteProperty(None, None, None, None, value)

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> 'ByteProperty':
        with StructIO(stream) as reader:
            value = reader.read(1)
            return ByteProperty(None, None, None, value, None)

    @classmethod
    def unpack_array(cls, stream: BinaryIO, count: int) -> bytes:
        with StructIO(stream) as reader:
            return reader.read(count)


@dataclass(unsafe_hash=True)
class IntProperty(Property):
    value: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'IntProperty':
        with StructIO(stream) as reader:
            flag = reader.read(1)
            assert flag == NULL, flag
            value = reader.unpack(Int32)
            return IntProperty(None, PropertyType.Int, None, value)

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> int:
        with StructIO(stream) as reader:
            return reader.unpack(Int32)

    @classmethod
    def unpack_array(cls, stream: BinaryIO, count: int) -> List[int]:
        with StructIO(stream) as reader:
            results = reader.unpack(f"{count}i")
            if count == 0:
                return []
            elif count == 1:
                return [results]
            else:
                return list(results)


@dataclass(unsafe_hash=True)
class Int64Property(Property):
    # unk_flag: bytes
    value: int

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'Int64Property':
        with StructIO(stream) as reader:
            flag = reader.read(1)
            assert flag == NULL, flag
            value = reader.unpack(Int64)
            return Int64Property(None, PropertyType.Int64, None, value)

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> 'Int64Property':
        with StructIO(stream) as reader:
            value = reader.unpack(Int64)
            return Int64Property(None, PropertyType.Int64, None, value)


@dataclass(unsafe_hash=True)
class BoolProperty(Property):
    # flag: bytes
    value: bytes

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'BoolProperty':
        with StructIO(stream) as reader:
            value, flag = reader.read(2)
            assert flag == 0, flag
            return BoolProperty(None, PropertyType.Bool, None, value)

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> 'BoolProperty':
        with StructIO(stream) as reader:
            value = reader.unpack("=c")
            return BoolProperty(None, PropertyType.Bool, None, value)


@dataclass(unsafe_hash=True)
class StructProperty(Property):
    abcd: Tuple[int,int,int,int]
    # e: bytes
    structure: Structure

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'StructProperty':
        with StructIO(stream, str_null_terminated=True) as reader:
            sub_type = reader.unpack_len_encoded_str()
            abcd = reader.unpack("=4I")
            e = reader.read(1)
            assert e == NULL, e

            structure = Structure.unpack_as_type(stream, sub_type)
            return StructProperty(None, PropertyType.Struct, None, abcd, structure)

    @classmethod
    def unpack_element(cls, stream: BinaryIO) -> 'StructProperty':
        # with StructIO(stream, str_null_terminated=True) as reader:
        structure = DynamicStructure.unpack(stream)
        return StructProperty(None, PropertyType.Struct, None, None, structure)

    @classmethod
    def unpack_array(cls, stream: BinaryIO, count: int) -> 'List[StructProperty]':
        with StructIO(stream, str_null_terminated=True) as reader:
            name = reader.unpack_len_encoded_str()
            assert name != str_NONE

            type = reader.unpack_len_encoded_str()
            parsed_type = PropertyType.parse(type)
            assert parsed_type == PropertyType.Struct

            size, index = reader.unpack("2I")

            sub_type = reader.unpack_len_encoded_str()

            abcd = reader.unpack("=4I")
            e = reader.read(1)
            assert e == NULL, e

            items = []
            for i in range(count):
                structure = Structure.unpack_as_type(stream, sub_type)

                prop = StructProperty(name, parsed_type, index, abcd, structure)
                items.append(prop)
            return items


@dataclass(unsafe_hash=True)
class NameProperty(Property):
    value: str

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'NameProperty':
        with StructIO(stream, str_null_terminated=True) as reader:
            a = reader.read(1)
            assert a == b'\x00', a
            name = reader.unpack_len_encoded_str()
            return NameProperty(None, None, None, name)


@dataclass(unsafe_hash=True)
class ArrayProperty(Property):

    array_type: PropertyType
    values: List

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'ArrayProperty':
        with StructIO(stream, str_null_terminated=True) as reader:
            sub_type = reader.unpack_len_encoded_str()
            parsed_type = PropertyType.parse(sub_type)
            a = reader.read(1)
            assert a == NULL, a
            count = reader.unpack(UInt32)
            array_unpacker = _unpack_array_map.get(parsed_type)
            element_unpacker = _unpack_element_map.get(parsed_type)
            if array_unpacker:
                items = array_unpacker(stream, count)
            elif element_unpacker:
                items = []
                for i in range(count):
                    item = element_unpacker(stream)
                    # item.name = f"Element {i}"
                    items.append(item)
            else:
                raise NotImplementedError("Cant unpack array of type", parsed_type)

            return ArrayProperty(None, None, None, parsed_type, items)


@dataclass(unsafe_hash=True)
class MapProperty(Property):
    # a: bytes
    # b: int
    key_type: PropertyType
    value_type: PropertyType
    map: Dict[Property, Property]

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'MapProperty':
        with StructIO(stream, str_null_terminated=True) as reader:
            key_type = reader.unpack_len_encoded_str()
            parsed_key = PropertyType.parse(key_type)
            key_unpacker = _unpack_element_map[parsed_key]

            value_type = reader.unpack_len_encoded_str()
            parsed_value = PropertyType.parse(value_type)
            value_unpacker = _unpack_element_map[parsed_value]

            a = reader.read(1)
            b = reader.unpack(UInt32)
            assert a == NULL, a
            assert b == 0, b

            count = reader.unpack(UInt32)
            map = {}

            for _ in range(count):
                key = key_unpacker(stream)
                value = value_unpacker(stream)

                map[key] = value
            return MapProperty(None, PropertyType.Map, None, parsed_key, parsed_value, map)


@dataclass(unsafe_hash=True)
class EnumProperty(Property):
    a: bytes
    enum_type: str
    enum_name: str

    @classmethod
    def unpack(cls, stream: BinaryIO) -> 'EnumProperty':
        with StructIO(stream, str_null_terminated=True) as reader:
            sub_type = reader.unpack_len_encoded_str()
            flag = reader.read(1)
            enum_name = reader.unpack_len_encoded_str()
            return EnumProperty(None, PropertyType.Enum, None, flag, sub_type, enum_name)


_unpack_map: Dict[PropertyType, Callable[[BinaryIO], Property]] = {
    PropertyType.Int: IntProperty.unpack,
    PropertyType.Float: FloatProperty.unpack,
    PropertyType.Bool: BoolProperty.unpack,
    PropertyType.Struct: StructProperty.unpack,
    PropertyType.Int64: Int64Property.unpack,
    PropertyType.Name: NameProperty.unpack,
    PropertyType.Array: ArrayProperty.unpack,
    PropertyType.Object: ObjectProperty.unpack,
    PropertyType.Map: MapProperty.unpack,
    PropertyType.Byte: ByteProperty.unpack,
    PropertyType.Enum: EnumProperty.unpack,
    PropertyType.String: StringProperty.unpack,
}
_unpack_element_map: Dict[PropertyType, Callable[[BinaryIO], Property]] = {
    PropertyType.Struct: StructProperty.unpack_element,
    PropertyType.Byte: ByteProperty.unpack_element,
    PropertyType.Object: ObjectPropertyData.unpack,
    PropertyType.Int: IntProperty.unpack_element,
}
_unpack_array_map: Dict[PropertyType, Callable[[BinaryIO, int], List[Property]]] = {
    PropertyType.Int: IntProperty.unpack_array,
    PropertyType.Struct: StructProperty.unpack_array,
    PropertyType.Byte: ByteProperty.unpack_array,
}

@dataclass
class ExcessDataProperty(Property):
    excess:bytes

class WorldObjectProperties:
    # properties: List[Property]
    # zero: int

    @classmethod
    def unpack(cls, stream: BinaryIO, size: int = None) -> Tuple[List[Property], int]:
        # Enforce null terminated for this particular run regardless of previous settings
        with StructIO(stream) as reader:
            if not size:
                read_size = size = reader.unpack(UInt32)
            bm = reader.tell()
            properties = []
            while True:
                prop = Property.unpack(stream)
                if prop:
                    properties.append(prop)
                else:
                    break
            zero = reader.unpack(UInt32)
            assert zero == 0, zero
            excess = (bm + size) - stream.tell()
            # excess_buffer = None

            if excess > 0:
                # excess_buffer = reader.read(excess)
                # properties.append(ExcessDataProperty("EXCESS DATA",None,None,excess_buffer))
                # print("WARNING DIDNT READ ENOUGH DATA!",excess,excess_buffer)
                # raise NotImplementedError("Didn't read enough data!", excess, excess_buffer)
                pass
            elif excess < 0:
                raise NotImplementedError("Read too much data!", excess)
            # else:
            #     excess_buffer = None
            # assert excess == 0, ("Start:",as_hex_adr(bm),"Size:", size,"Now:", as_hex_adr(stream.tell()), "Remaining Bytes:", excess, "Remaining:",excess_buffer)
        return properties, excess
