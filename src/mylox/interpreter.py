from __future__ import annotations

from .errors import LoxRuntimeError
from .nodes import Binary, Grouping, Literal, Node, Unary, Visitor
from .tokens import Token, TokenKind


class Interpreter(Visitor):
    """
    Convierte nodos del arbol en valores de Lox recorriendo el tree-walk interpreter
    """

    def evaluate(self, expression: Node) -> object:
        """Evalúa una expresión y devuelve el valor resultante."""
        return expression.accept(self)

    def visit_literal(self, expression: Literal) -> object:
        raise NotImplementedError()

    def visit_grouping(self, expression: Grouping) -> object:
        raise NotImplementedError()

    def visit_unary(self, expression: Unary) -> object:
        raise NotImplementedError()

    def visit_binary(self, expression: Binary) -> object:
        raise NotImplementedError()