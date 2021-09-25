from typing import Union

from wizki.utils import cached_function, TypedBytes


PRIMITIVE_TYPES = {
    "std::wstring": 1293773415,
    "unsigned __int64": 472810120,
    "unsigned int": 211490908,
    "float": 90289606,
    "char": 2624835,
    "bui2": 536290,
    "bi4": 22882,
    "bi3": 17762,
    "bi2": 16738,
    "s24": 21011,
    "bi6": 20834,
    "bi7": 21858,
    "u24": 21013,
    "bf4": 22658,
    "gid": 72039,
    "bi5": 23906,
    "bf8": 26754,
    "int": 88457,
    "bui4": 732898,
    "bui6": 667362,
    "bui3": 569058,
    "bui7": 700130,
    "buf4": 725730,
    "bui5": 765666,
    "bf16": 740482,
    "buf8": 856802,
    "long": 2273708,
    "bool": 2569634,
    "char*": 8916291,
    "buf16": 23696098,
    "short": 90715475,
    "__int64": 694559706,
    "unsigned short": 553670903,
    "unsigned char": 637687903,
    "union gid": 993596468,
    "std::string": 1497788074,
    "unsigned long": 1906292832,
    "double": 1897898588,
    "wchar_t": 2063706146,
    "wchar_t*": 2063706226
}


def override_class_name(new_name: str):
    def _decorator(class_):
        class_._override_name = new_name
        return class_

    return _decorator


class PropertyClass:
    def __init__(self, data_stream: Union[TypedBytes, bytes]):
        if isinstance(data_stream, bytes):
            data_stream = TypedBytes(data_stream)

        self._from_data(data_stream)

    def __hash__(self):
        if (name := getattr(self, "_override_name")) is None:
            name = type(self).__name__

        # return ki_generic_hash(name)
        return 1

    def _from_data(self, data_stream: TypedBytes):
        for attr_name in dir(self):
            attr_value = getattr(self, attr_name)

            # hash: Property
            hash_map = {}

            if isinstance(attr_value, Property):
                hash_map[attr_value.as_hash(attr_name)] = attr_value

            # do stuff to get next hash here
            next_hash = None
            # noinspection PyProtectedMember
            new_value = hash_map[next_hash]._from_data(data_stream)

            setattr(self, attr_name, new_value)


class Property:
    def __init__(
            self,
            type_name: str,
            *,
            override_name: str,
            flags: int,
    ):
        if type_name not in PRIMITIVE_TYPES:
            raise ValueError(f"{type_name} is not a primitive type.")

        self.type_name = type_name
        self.override_name = override_name
        self.flags = flags

    # can't use __hash__ since we need the property name
    # TODO: make sure cached_function works for subclasses
    @cached_function
    def as_hash(self, propery_name: str):
        # long m_test => djb2("m_test") + ki_generic_hash("long")
        name = self.override_name or propery_name
        # return djb2(name) + PRIMITIVE_TYPES[self.type_name]
        return 1

    def _from_data(self, data_stream: TypedBytes):
        return 1


class Container(Property):
    pass
