"""Representación textual del AST para inspección mediante el modo --tree.

El visitante describe los nodos sin ejecutar el programa, leer variables
ni producir los efectos de sus sentencias.
"""

from __future__ import annotations

from .nodes import (
    Assign, Binary, BlockStmt, Call, ExprStmt, FunctionDecl, Grouping, IfStmt,
    Literal, Logical, Node, PrintStmt, ReturnStmt, Unary, VarDecl, Variable,
    Visitor, WhileStmt,
)


class Impresor(Visitor):
    """Visitante que devuelve texto con el tipo y contenido de cada nodo.

    Los hijos se describen recursivamente mediante ``accept(self)``. Los
    valores literales usan la representación de Python para depurar el AST;
    este texto no pretende ser la salida del programa ni código fuente Lox.
    """

    def visit_literal(self, expression: Literal) -> str:
        """Describe el valor almacenado usando repr, por ejemplo Literal(1.0)."""
        return f"Literal({expression.value!r})"

    def visit_unary(self, expression: Unary) -> str:
        """Describe el lexema del prefijo y visita su único operando.

        Devuelve la estructura Unary sin aplicar la negación o el not.
        """
        return f"Unary({expression.operator.lexeme!r}, {expression.operand.accept(self)})"

    def visit_binary(self, expression: Binary) -> str:
        """Describe izquierda, operador y derecha conservando el orden del AST.

        Visita recursivamente ambos operandos y devuelve su estructura Binary
        sin calcular el resultado de la operación.
        """
        return (
            f"Binary({expression.left.accept(self)}, "
            f"{expression.operator.lexeme!r}, "
            f"{expression.right.accept(self)})"
        )

    def visit_grouping(self, expression: Grouping) -> str:
        """Describe Grouping con el texto obtenido al visitar su expresión interior."""
        return f"Grouping({expression.expression.accept(self)})"

    def visit_call(self, expression: Call) -> str:
        args = ", ".join(arg.accept(self) for arg in expression.arguments)
        return f"Call({expression.callee.accept(self)}, args=[{args}])"

    def visit_logical(self, expression: Logical) -> str:
        return f"Logical({expression.left.accept(self)}, {expression.operator.lexeme!r}, {expression.right.accept(self)})"

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

    def visit_if_stmt(self, statement: IfStmt) -> str:
        """Describe la condición y las dos ramas de if presentes en el AST.

        Usa el texto ``None`` cuando no hay else. Describe ambas ramas
        disponibles sin evaluar la condición ni seleccionar una para ejecutar.
        """
        other = statement.else_branch.accept(self) if statement.else_branch else "None"
        return (
            f"IfStmt({statement.condition.accept(self)}, "
            f"{statement.then_branch.accept(self)}, {other})"
        )

    def visit_while_stmt(self, statement: WhileStmt) -> str:
        """Describe una vez la condición y el cuerpo de WhileStmt, sin iterar."""
        return f"WhileStmt({statement.condition.accept(self)}, {statement.body.accept(self)})"

    def visit_function_decl(self, statement: FunctionDecl) -> str:
        """Describe nombre, parámetros y cuerpo de fun sin crear una función."""
        parameters = ", ".join(repr(parameter.lexeme) for parameter in statement.parameters)
        body = ", ".join(item.accept(self) for item in statement.body)
        return f"FunctionDecl({statement.name.lexeme!r}, [{parameters}], [{body}])"

    def visit_return_stmt(self, statement: ReturnStmt) -> str:
        """Describe return y su posible expresión sin abandonar ningún cuerpo."""
        value = statement.value.accept(self) if statement.value is not None else "nil"
        return f"ReturnStmt({value})"




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
