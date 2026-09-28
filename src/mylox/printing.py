from __future__ import annotations
from .nodes import Binary, ExprStmt, Grouping, Literal, Node, PrintStmt, Unary, Visitor

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

    def visit_expr_stmt(self, statement: ExprStmt) -> str:
        """Envuelve la descripción de la expresión en ExprStmt, sin evaluarla."""
        return f"ExprStmt({statement.expression.accept(self)})"

    def visit_print_stmt(self, statement: PrintStmt) -> str:
        """Describe PrintStmt y su expresión sin ejecutar el print de Lox."""
        return f"PrintStmt({statement.expression.accept(self)})"


def imprimir(nodo: Node | list[Node]) -> str:
    """Devuelve la descripción de un nodo o de una lista que forma un programa.

    Crea un Impresor y despacha mediante accept. Para un programa une el texto
    de cada sentencia con saltos de línea; una lista vacía produce una cadena
    vacía. El llamador decide dónde mostrar el texto devuelto.
    """
    visitor = Impresor()
    if isinstance(nodo, list):
        return "\n".join(statement.accept(visitor) for statement in nodo)
    return nodo.accept(visitor)
