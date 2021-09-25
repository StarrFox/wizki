import struct
from typing import Tuple
from io import BytesIO


# yea I do copy paste this everywhere
type_format_dict = {
    "char": "<c",
    "signed char": "<b",
    "unsigned char": "<B",
    "bool": "?",
    "short": "<h",
    "unsigned short": "<H",
    "int": "<i",
    "unsigned int": "<I",
    "long": "<l",
    "unsigned long": "<L",
    "long long": "<q",
    "unsigned long long": "<Q",
    "float": "<f",
    "double": "<d",
}


class TypedBytes(BytesIO):
    def split(self, index: int) -> Tuple["TypedBytes", "TypedBytes"]:
        self.seek(0)
        buffer = self.read(index)
        return type(self)(buffer), type(self)(self.read())

    def read_typed(self, type_name: str):
        type_format = type_format_dict[type_name]
        size = struct.calcsize(type_format)
        data = self.read(size)
        return struct.unpack(type_format, data)[0]
