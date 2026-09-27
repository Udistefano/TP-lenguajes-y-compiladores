from __future__ import annotations

from dataclasses import dataclass


class ReturnValue(Exception):
    """Cuando un statement "return" evalúa su valor, lanza esta excepción, la función que está ejecutando el 
    cuerpo la captura y devuelve el valor. No es un error de usuario, por eso no sale de LoxError.
    """

    def __init__(self, value: object) -> None:
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
        """Ejecuta el cuerpo de la función por invocación."""
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
        return f"<fn {self.declaration.name.lexeme}>"