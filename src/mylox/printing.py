from __future__ import annotations
from .nodes import Binary, Grouping, Literal, Node, Unary, Visitor

class Impresor(Visitor):
    """Convierte un árbol de nodos en una representación textual verbosa."""

    def visit_literal(self, expression: Literal) -> str:
        return f"Literal({expression.value!r})"

    def visit_unary(self, expression: Unary) -> str:
        return f"Unary({expression.operator.lexeme!r}, {expression.operand.accept(self)})"

    def visit_binary(self, expression: Binary) -> str:
        return (
            f"Binary({expression.left.accept(self)}, "
            f"{expression.operator.lexeme!r}, "
            f"{expression.right.accept(self)})"
        )

    def visit_grouping(self, expression: Grouping) -> str:
        return f"Grouping({expression.expression.accept(self)})"


def imprimir(nodo: Node) -> str:
    """Devuelve la representación verbosa del árbol de expresiones recibido."""

    return nodo.accept(Impresor())