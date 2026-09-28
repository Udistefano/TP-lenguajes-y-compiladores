"""Vínculos léxicos de variables antes de ejecutar el programa.

Este Visitor recorre el mismo AST que Interpreter, pero sólo registra nombres
y ámbitos. Una referencia local guarda cuántos ambientes hay que subir desde
el punto de ejecución. Las referencias sin vínculo local usan el global.
"""

from __future__ import annotations

from .errors import ParseError
from .nodes import (
    Assign, Binary, BlockStmt, Call, ExprStmt, FunctionDecl, Grouping, IfStmt,
    Literal, Logical, Node, PrintStmt, ReturnStmt, Unary, VarDecl, Variable,
    Visitor, WhileStmt,
)
from .tokens import Token


class BindingResolver(Visitor):
    """Determina el ámbito de cada lectura o asignación sin evaluar valores.

    Cada conjunto de _scope_names representa un bloque o una invocación.
    Se visitan las declaraciones en orden: una función no puede capturar una
    variable local declarada después de ella. Los globales se consultarán en
    ejecución, lo que permite funciones globales que se llaman mutuamente.
    """

    def __init__(self) -> None:
        """Inicia un recorrido sin ámbitos locales ni funciones activas.

        local_bindings asocia la identidad de un nodo con el nodo y su
        distancia léxica. Conservar el objeto evita reutilizar su identidad
        cuando una misma instancia de Interpreter ejecuta varios programas.
        """
        self._scope_names: list[set[str]] = []
        self._inside_functions = 0
        self.local_bindings: dict[int, tuple[Node, int]] = {}

    def resolve_program(self, statements: list[Node]) -> dict[int, tuple[Node, int]]:
        """Recorre el programa y entrega sus vínculos locales al intérprete.

        Los cuerpos de funciones también se recorren ahora, aunque se llamen
        más tarde. Un return fuera de una función produce ParseError antes
        de ejecutar cualquier sentencia del programa.
        """
        for statement in statements:
            statement.accept(self)
        return self.local_bindings

    def _walk_scope(self, statements: list[Node], names: tuple[str, ...] = ()) -> None:
        """Visita un cuerpo con un ámbito local y luego restaura el exterior.

        names contiene los parámetros si el cuerpo pertenece a una función.
        Cada ámbito agregado aquí corresponde a un Env que la ejecución
        creará; el finally mantiene la pila consistente ante un error.
        """
        self._scope_names.append(set(names))
        try:
            for statement in statements:
                statement.accept(self)
        finally:
            self._scope_names.pop()

    def _register(self, name: Token) -> None:
        """Hace visible una declaración en el ámbito local actual, si existe."""
        if self._scope_names:
            self._scope_names[-1].add(name.lexeme)

    def _link(self, expression: Node, name: Token) -> None:
        """Registra la distancia al ámbito local más cercano con este nombre.

        Cero señala el Env activo, uno su padre, y así sucesivamente.
        Si no encuentra un local, no agrega una entrada: esa referencia
        consultará el ambiente global, incluso dentro de un closure.
        """
        for levels, names in enumerate(reversed(self._scope_names)):
            if name.lexeme in names:
                self.local_bindings[id(expression)] = (expression, levels)
                return

    def visit_literal(self, expression: Literal) -> None:
        """Los literales no contienen nombres que necesiten vincularse."""

    def visit_grouping(self, expression: Grouping) -> None:
        """Recorre la expresión agrupada sin crear un ámbito de variables."""
        expression.expression.accept(self)

    def visit_unary(self, expression: Unary) -> None:
        """Recorre el operando sin aplicar su operador prefijo."""
        expression.operand.accept(self)

    def visit_binary(self, expression: Binary) -> None:
        """Vincula las referencias de ambos operandos sin calcular resultados."""
        expression.left.accept(self)
        expression.right.accept(self)

    def visit_logical(self, expression: Logical) -> None:
        """Recorre ambos lados; el corto circuito corresponde a la ejecución."""
        expression.left.accept(self)
        expression.right.accept(self)

    def visit_call(self, expression: Call) -> None:
        """Recorre el callee y todos sus argumentos sin invocar la función."""
        expression.callee.accept(self)
        for argument in expression.arguments:
            argument.accept(self)

    def visit_variable(self, expression: Variable) -> None:
        """Fija el ámbito visible para esta lectura de variable."""
        self._link(expression, expression.name)

    def visit_assign(self, expression: Assign) -> None:
        """Recorre el valor y fija el ámbito que modificará la asignación."""
        expression.value.accept(self)
        self._link(expression, expression.name)

    def visit_var_decl(self, statement: VarDecl) -> None:
        """Recorre el inicializador y luego hace visible el nombre declarado.

        Mantiene el orden de nuestra ejecución de var: el inicializador
        puede leer nombres que ya estaban disponibles antes de la declaración.
        """
        if statement.initializer is not None:
            statement.initializer.accept(self)
        self._register(statement.name)

    def visit_function_decl(self, statement: FunctionDecl) -> None:
        """Registra fun antes de recorrer su cuerpo para permitir recursión.

        El ámbito de parámetros coincide con el Env creado por Function.call.
        El contador permite return en funciones anidadas y se restaura al
        terminar el recorrido de cada declaración.
        """
        self._register(statement.name)
        self._inside_functions += 1
        try:
            names = tuple(parameter.lexeme for parameter in statement.parameters)
            self._walk_scope(statement.body, names)
        finally:
            self._inside_functions -= 1

    def visit_return_stmt(self, statement: ReturnStmt) -> None:
        """Exige un contexto de función y vincula la expresión del retorno."""
        if self._inside_functions == 0:
            token = statement.keyword
            raise ParseError(
                f"return fuera de una función en la línea {token.line}, "
                f"columna {token.column}"
            )
        if statement.value is not None:
            statement.value.accept(self)

    def visit_expr_stmt(self, statement: ExprStmt) -> None:
        """Recorre la expresión de la sentencia sin ejecutar sus efectos."""
        statement.expression.accept(self)

    def visit_print_stmt(self, statement: PrintStmt) -> None:
        """Recorre la expresión de print sin escribir en stdout."""
        statement.expression.accept(self)

    def visit_block_stmt(self, statement: BlockStmt) -> None:
        """Agrega un ámbito léxico para las declaraciones entre llaves."""
        self._walk_scope(statement.statements)

    def visit_if_stmt(self, statement: IfStmt) -> None:
        """Recorre condición y ramas sin decidir cuál se ejecutará."""
        statement.condition.accept(self)
        statement.then_branch.accept(self)
        if statement.else_branch is not None:
            statement.else_branch.accept(self)

    def visit_while_stmt(self, statement: WhileStmt) -> None:
        """Recorre condición y cuerpo una vez sin repetir el bucle."""
        statement.condition.accept(self)
        statement.body.accept(self)
