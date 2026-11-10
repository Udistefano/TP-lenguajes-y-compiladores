"""Clases de runtime para la programación orientada a objetos de Lox."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .env import Env
    from .interpreter import Interpreter
    from .nodes import FunctionDecl

from .function import ReturnValue
from .errors import LoxRuntimeError


@dataclass
class LoxInstance:
    """Una instancia de una clase Lox.

    Las propiedades se guardan en ``fields``; los métodos se buscan en la
    clase (y en las superclases) y se ligan a esta instancia al accederlos.
    """

    klass: "LoxClass"
    fields: dict[str, object] = field(default_factory=dict)

    def get(self, name: "Token") -> object:
        """Devuelve el valor de la propiedad o método con ese nombre."""
        if name.lexeme in self.fields:
            return self.fields[name.lexeme]
        method = self.klass.find_method(name.lexeme)
        if method is not None:
            return method.bind(self)
        raise LoxRuntimeError(name, f"Undefined property '{name.lexeme}'.")

    def set(self, name: "Token", value: object) -> None:
        """Guarda el valor en una propiedad de la instancia."""
        self.fields[name.lexeme] = value

    def __str__(self) -> str:
        return f"{self.klass.name} instance"


@dataclass
class LoxClass:
    """Una clase Lox, con su superclase y sus métodos.

    Las clases son callables: instanciar crea una LoxInstance y ejecuta
    ``init`` si existe.
    """

    name: str
    superclass: "LoxClass | None"
    methods: dict[str, "LoxFunction"]

    def find_method(self, name: str) -> "LoxFunction | None":
        """Busca un método en esta clase o en las superclases."""
        if name in self.methods:
            return self.methods[name]
        if self.superclass is not None:
            return self.superclass.find_method(name)
        return None

    @property
    def arity(self) -> int:
        """Cantidad de argumentos que espera el constructor (init)."""
        initializer = self.find_method("init")
        if initializer is None:
            return 0
        return initializer.arity

    def call(self, interpreter: "Interpreter", arguments: list[object]) -> object:
        """Crea una instancia y ejecuta ``init`` si existe."""
        instance = LoxInstance(self)
        initializer = self.find_method("init")
        if initializer is not None:
            initializer.bind(instance).call(interpreter, arguments)
        return instance

    def is_callable(self) -> bool:
        """Las clases son invocables (se instancian)."""
        return True

    def __str__(self) -> str:
        return self.name


@dataclass
class LoxFunction:
    """Una función Lox, que puede ser un método o una función libre.

    ``is_initializer`` indica si es el constructor ``init`` de una clase.
    ``bind`` crea una copia con ``this`` inyectado en el closure.
    ``instance`` guarda la instancia vinculada (solo para métodos).
    """

    declaration: "FunctionDecl"
    closure: "Env"
    is_initializer: bool
    instance: "LoxInstance | None" = None

    @property
    def arity(self) -> int:
        """Cantidad de parámetros que la función espera recibir."""
        return len(self.declaration.parameters)

    def bind(self, instance: "LoxInstance") -> "LoxFunction":
        """Crea una copia de la función con ``this`` en su closure."""
        from .env import Env

        environment = Env(enclosing=self.closure)
        environment.define("this", instance)
        return LoxFunction(self.declaration, environment, self.is_initializer, instance)

    def call(self, interpreter: "Interpreter", arguments: list[object]) -> object:
        """Ejecuta el cuerpo en un ámbito nuevo encadenado al closure."""
        from .env import Env

        environment = Env(enclosing=self.closure)

        for param, argument in zip(self.declaration.parameters, arguments):
            environment.define(param.lexeme, argument)

        try:
            interpreter.execute_block(self.declaration.body, environment)
        except ReturnValue as return_value:
            if self.is_initializer:
                return self.instance
            return return_value.value
        if self.is_initializer:
            return self.instance
        return None

    def __str__(self) -> str:
        """Muestra el nombre de Lox cuando print recibe esta función."""
        return f"<fn {self.declaration.name.lexeme}>"