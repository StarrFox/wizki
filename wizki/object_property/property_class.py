class PropertyClass:
    def __init__(self, data_stream: bytes):
        pass


class Property:
    def __init__(
            self,
            type_name: str,
            *,
            override_name: str,
            flags: int,
    ):
        # check if type_name is in primitive list
        self.type_name = type_name
        self.override_name = override_name
        self.flags = flags


class Container(Property):
    pass




