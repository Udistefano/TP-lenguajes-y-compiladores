from __future__ import annotations

from dataclasses import dataclass


class ListError(Exception):
    pass


def require_list(value: object) -> LoxList:
    if not isinstance(value, LoxList):
        raise ListError("Only lists can be indexed.")
    return value


@dataclass(eq=False, slots=True)
class LoxList:
    items: list[object]

    def position(self, index: object) -> int:
        if not isinstance(index, float) or not index.is_integer():
            raise ListError("List index must be an integer.")
        if not 0 <= index < len(self.items):
            raise ListError("List index out of bounds.")
        return int(index)

    def get(self, index: object) -> object:
        return self.items[self.position(index)]

    def set(self, index: object, value: object) -> object:
        self.items[self.position(index)] = value
        return value

    def get_property(self, name: str) -> object:
        if name == "length":
            return float(len(self.items))
        if name in ("push", "pop"):
            return ListMethod(self, name)
        raise ListError(f"Undefined list property '{name}'.")


@dataclass(eq=False, slots=True)
class ListMethod:
    receiver: LoxList
    name: str

    @property
    def arity(self) -> int:
        return 1 if self.name == "push" else 0

    def invoke(self, arguments: list[object]) -> object:
        if self.name == "push":
            self.receiver.items.append(arguments[0])
            return None
        if not self.receiver.items:
            raise ListError("Cannot pop an empty list.")
        return self.receiver.items.pop()

    def __str__(self) -> str:
        return f"<list.{self.name}>"
