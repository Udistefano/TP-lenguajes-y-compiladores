from __future__ import annotations
from dataclasses import dataclass
from .tokens import Token


class Node:
    """
    Clase base para todos los nodos del árbol. Cada nodo debe implementar el
    método accept() para permitir que un visitante recorra el árbol y realice
    operaciones sobre los nodos.
    """

    def accept(self, visitor: Visitor) -> object:
        raise NotImplementedError(
            f"{type(self).__name__} no implementa accept()"
        )


class Visitor:
    """
    interfaz para los visitantes que pueden recorrer el árbol de
    nodos y realizar operaciones sobre ellos.
    """

    def visit_literal(self, expression: Literal) -> object:
        raise NotImplementedError()

    def visit_unary(self, expression: Unary) -> object:
        raise NotImplementedError()

    def visit_binary(self, expression: Binary) -> object:
        raise NotImplementedError()

    def visit_grouping(self, expression: Grouping) -> object:
        raise NotImplementedError()


@dataclass(frozen=True, slots=True)
class Literal(Node):
    """puede ser un número, una cadena o un booleano."""

    value: float | str | bool | None

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_literal(self)


@dataclass(frozen=True, slots=True)
class Unary(Node):
    """consiste en un operador y un operando."""

    operator: Token
    operand: Node

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_unary(self)


@dataclass(frozen=True, slots=True)
class Binary(Node):
    """consiste en un operador y dos operandos."""

    left: Node
    operator: Token
    right: Node

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_binary(self)


@dataclass(frozen=True, slots=True)
class Grouping(Node):
    """expresión entre paréntesis."""

    expression: Node

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_grouping(self)