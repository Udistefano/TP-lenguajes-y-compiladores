"""Almacenamiento de variables en ambientes encadenados de Lox."""

from __future__ import annotations

from .errors import LoxRuntimeError
from .tokens import Token


class Env:
    """Relaciona los nombres de un ámbito con sus valores de Lox.

    ``values`` contiene solamente las variables de este ámbito. ``enclosing``
    apunta al ámbito exterior, o es None en el global. Leer y asignar recorren
    esa cadena desde el ámbito más cercano; declarar opera en el actual.
    """

    def __init__(self, enclosing: Env | None = None) -> None:
        """Crea un ámbito sin variables y conserva su posible ambiente padre.

        Se enlaza el objeto padre sin copiar sus variables, de modo que una
        asignación exterior pueda ser observada desde los ámbitos internos.
        """
        self.enclosing = enclosing
        self.values: dict[str, object] = {}

    def define(self, name: str, value: object) -> None:
        """Guarda el nombre y su valor en este ámbito y devuelve None.

        Recibe el texto del nombre, no su Token. Si ya estaba declarado aquí,
        reemplaza su valor; si existe en un padre, crea una variable local
        que lo sombrea. Un valor None representa una variable declarada con nil.
        """
        self.values[name] = value

    def get(self, name: Token) -> object:
        """Devuelve el valor del nombre más cercano en la cadena de ámbitos.

        Usa ``name.lexeme`` como clave. Comprueba la presencia de esa clave,
        por lo que nil, false y cero siguen siendo valores de variables
        definidas. Si ningún ámbito contiene el nombre, lanza LoxRuntimeError
        con el token recibido para informar dónde se intentó leerlo.
        """
        if name.lexeme in self.values:
            return self.values[name.lexeme]
        if self.enclosing is not None:
            return self.enclosing.get(name)
        raise LoxRuntimeError(name, f"Variable indefinida {name.lexeme!r}")

    def assign(self, name: Token, value: object) -> None:
        """Reemplaza el valor del primer ámbito que contiene el nombre.

        Busca desde este ambiente hacia los exteriores usando ``name.lexeme``.
        Devuelve None después de modificar la entrada y no crea variables.
        Si el nombre no fue declarado en la cadena, lanza LoxRuntimeError
        con el token de la asignación.
        """
        if name.lexeme in self.values:
            self.values[name.lexeme] = value
            return
        if self.enclosing is not None:
            self.enclosing.assign(name, value)
            return
        raise LoxRuntimeError(name, f"Variable indefinida {name.lexeme!r}")
