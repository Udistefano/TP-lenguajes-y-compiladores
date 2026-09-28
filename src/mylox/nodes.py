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

    def visit_expr_stmt(self, statement: ExprStmt) -> object:
        """Define la operación sobre una expresión usada como sentencia."""
        raise NotImplementedError()

    def visit_print_stmt(self, statement: PrintStmt) -> object:
        """Define la operación sobre una sentencia print y su expresión."""
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


@dataclass(frozen=True, slots=True)
class ExprStmt(Node):
    """Representa una expresión terminada por punto y coma, como ``2 + 3;``.

    ``expression`` guarda el cálculo. Al ejecutar esta sentencia,
    Interpreter conserva sus efectos y descarta el valor devuelto.
    """

    expression: Node

    def accept(self, visitor: Visitor) -> object:
        """Selecciona ``visit_expr_stmt`` para visitar la sentencia completa."""
        return visitor.visit_expr_stmt(self)


@dataclass(frozen=True, slots=True)
class PrintStmt(Node):
    """Representa ``print expresión;`` y conserva la expresión a mostrar.

    El nodo contiene la estructura; el visitante decide cómo ejecutarla
    o describirla. Interpreter evalúa su expresión y escribe el valor.
    """
    expression: Node

    def accept(self, visitor: Visitor) -> object:
        """Selecciona ``visit_print_stmt`` para visitar la sentencia completa."""
        return visitor.visit_print_stmt(self)
