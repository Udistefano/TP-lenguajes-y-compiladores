"""Objetos de runtime para funciones compiladas a bytecode"""
from __future__ import annotations

from .chunk import Chunk


class Upvalue:
    """Una variable capturada por un closure.

    Mientras el scope que la declaró siga vivo, ``stack_index`` apunta a su
    posición en el stack. Al cerrarse, el valor se copia a ``closed_value`` y
    ``stack_index`` queda en None.
    """

    def __init__(self, stack_index: int | None = None) -> None:
        self.stack_index = stack_index
        self.closed_value: object | None = None


class Function:
    """Una función cruda: lo que se sabe en tiempo de compilación.

    El chunk y la aridad no dependen de que la función esté viva: son datos
    estáticos que el compilador produce y la VM consume.
    """

    def __init__(self, name: str | None) -> None:
        self.name = name
        self.chunk = Chunk()
        self.arity = 0
        self.upvalue_count = 0
        self.is_initializer = False

    def __repr__(self) -> str:
        if self.name is None:
            return "<script>"
        return f"<fn {self.name}()>"


class Closure:
    """Una función viva en runtime, con sus upvalues capturados."""

    def __init__(self, function: Function) -> None:
        self.function = function
        self.code = function.chunk.code
        self.constants = function.chunk.constants
        self.upvalues: list = []

    def __repr__(self) -> str:
        return f"<cls {self.function.name}()>"

    def __str__(self) -> str:
        return f"<fn {self.function.name}>"


class CallFrame:
    """Marco de una invocación: qué función se está ejecutando, dónde
    sigue el ip y desde qué slot del stack viven sus locales.
    """

    def __init__(self, closure: Closure, stack_slot: int) -> None:
        self.closure = closure
        self.code = closure.code
        self.constants = closure.constants
        self.ip = 0
        self.stack_slot = stack_slot


class BoundMethod:
    """Un método ligado a una instancia, para el backend bytecode.

    Guarda la instancia (receiver) y el closure del método. Al llamarlo,
    la VM reemplaza este objeto en el stack por la instancia, de modo que
    ``this`` (slot 0 del frame) la reciba como primer slot.
    """

    def __init__(self, instance: object, method: Closure) -> None:
        self.instance = instance
        self.method = method

    @property
    def function(self) -> Function:
        """La función cruda del método ligado."""
        return self.method.function

    @property
    def arity(self) -> int:
        """Cantidad de argumentos que espera el método (sin contar ``this``)."""
        return self.method.function.arity

    def __repr__(self) -> str:
        return f"<bound {self.method.function.name}>"

    def __str__(self) -> str:
        return str(self.method)
