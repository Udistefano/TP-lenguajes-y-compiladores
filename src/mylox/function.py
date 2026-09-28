from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .env import Env
    from .interpreter import Interpreter
    from .nodes import FunctionDecl


class ReturnValue(Exception):
    """Cuando un statement "return" evalúa su valor, lanza esta excepción, la función que está ejecutando el 
    cuerpo la captura y devuelve el valor. No es un error de usuario, por eso no sale de LoxError.
    """

    def __init__(self, value: object) -> None:
        """Conserva el valor que Function.call recuperará al capturar el retorno."""
        self.value = value
        super().__init__("función devolvió un valor")


@dataclass(frozen=True, slots=True)
class Function:
    """
    Representa una función de Lox ( como en la pag 92)
    Guarda la declaración (FunctionDecl) y el closure donde fue
    definida para ejecutar su cuerpo conservando el ámbito capturado
    """

    declaration: FunctionDecl
    closure: Env

    @property
    def arity(self) -> int:
        """Cantidad de parámetros que la función espera recibir."""

        return len(self.declaration.parameters)

    def call(self, interpreter: Interpreter, arguments: list[object]) -> object:
        """Ejecuta el cuerpo en un ámbito nuevo encadenado al closure.

        Cada llamada tiene sus propios parámetros y variables locales.
        execute_block restaura el ámbito del llamador al salir; ReturnValue
        transporta una salida anticipada. Llegar al final devuelve nil.
        """
        from .env import Env

        environment = Env(enclosing=self.closure)

        for param, argument in zip(self.declaration.parameters, arguments):
            environment.define(param.lexeme, argument)

        try:
            interpreter.execute_block(self.declaration.body, environment)
        except ReturnValue as return_value:
            return return_value.value
        return None

    def __str__(self) -> str:
        """Muestra el nombre de Lox cuando print recibe esta función como valor."""
        return f"<fn {self.declaration.name.lexeme}>"
