import dataclasses
import json
import typing
from dataclasses import Field, fields
from http import client
from typing import Final, override, get_type_hints

JsonType = (
        dict[dict | list | str | int] |
        list[dict | list | str | int] |
        str |
        int
)


class Json:
    """jsonを扱うクラス
    :var json_value: jsonを表す辞書
    """
    json_value: Final[JsonType]

    def __init__(self, json_value: JsonType):
        self.json_value = json_value

    def dumps(self) -> str:
        return json.dumps(self.json_value)

    @staticmethod
    def by_str(json_str: str):
        """文字列からJsonを作成します
        """
        return Json(json.loads(json_str))

    @staticmethod
    def by_response(json_response: client.HTTPResponse):
        """文字列からJsonを作成します
        """
        return Json(json.load(json_response))

    @override
    def __str__(self):
        return self.json_value.__str__()

    def to_dataclass(self, clazz):
        return Json.dict_to_dataclass(self.json_value, clazz)

    @staticmethod
    def dict_to_dataclass[T](src: JsonType, clazz: type[T]) -> T:
        generic_types = typing.get_args(clazz)
        if clazz == any:
            return clazz(src)

        if clazz == list[*generic_types]:
            result = list()
            if len(generic_types) == 0:
                element_type = any
            else:
                element_type = generic_types[0]
            for item in src:
                result.append(
                    Json.dict_to_dataclass(item, element_type)
                )
            return result

        result = dict()
        field_dict: dict[str, Field] = {field.name: field for field in fields(clazz)}
        field_type_dict: dict[str, type] = get_type_hints(clazz)
        for src_key, src_value in src.items():
            if src_key not in field_type_dict:
                continue
            field = field_dict[src_key]
            field_type = field_type_dict[field.name]
            if dataclasses.is_dataclass(field_type):
                result[src_key] = Json.dict_to_dataclass(src_value, field_type)
            else:
                result[src_key] = src_value
        return clazz(**result)
