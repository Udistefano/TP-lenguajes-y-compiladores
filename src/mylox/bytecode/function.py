"""Objetos de runtime para funciones compiladas a bytecode"""
from __future__ import annotations

from .chunk import Chunk


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

    def __repr__(self) -> str:
        if self.name is None:
            return "<script>"
        return f"<fn {self.name}()>"


class Closure:
    """Una función viva en runtime, con sus upvalues capturados."""

    def __init__(self, function: Function) -> None:
        self.function = function
        self.upvalues: list = []

    def __repr__(self) -> str:
        return f"<cls {self.function.name}()>"


class CallFrame:
    """Marco de una invocación: qué función se está ejecutando, dónde
    sigue el ip y desde qué slot del stack viven sus locales.
    """

    def __init__(self, closure: Closure, stack_slot: int) -> None:
        self.closure = closure
        self.ip = 0
        self.stack_slot = stack_slot
