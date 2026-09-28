from __future__ import annotations
from .nodes import (
    Assign, Binary, BlockStmt, ExprStmt, Grouping, Literal, Node,
    PrintStmt, Unary, VarDecl, Variable, Visitor,
)

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

    def visit_var_decl(self, statement: VarDecl) -> str:
        """Describe el nombre y el inicializador de una declaración var.

        Si no hay inicializador, usa el texto ``nil``. No define el nombre
        en un ambiente ni evalúa el posible subárbol inicializador.
        """
        initializer = statement.initializer.accept(self) if statement.initializer else "nil"
        return f"VarDecl({statement.name.lexeme!r}, {initializer})"

    def visit_variable(self, expression: Variable) -> str:
        """Describe el nombre de una referencia sin consultar su valor en Env."""
        return f"Variable({expression.name.lexeme!r})"

    def visit_assign(self, expression: Assign) -> str:
        """Describe el nombre destino y visita el AST del valor sin asignarlo."""
        return f"Assign({expression.name.lexeme!r}, {expression.value.accept(self)})"

    def visit_block_stmt(self, statement: BlockStmt) -> str:
        """Describe la lista del bloque visitando sus nodos en orden.

        Devuelve BlockStmt con los textos de sus hijos separados por comas;
        no crea un ambiente ni ejecuta las sentencias del cuerpo.
        """
        statements = ", ".join(item.accept(self) for item in statement.statements)
        return f"BlockStmt([{statements}])"


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
