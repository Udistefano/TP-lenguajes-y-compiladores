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

    def visit_variable(self, expression: Variable) -> object:
        """Define la operación sobre una referencia a un nombre de variable."""
        raise NotImplementedError()

    def visit_assign(self, expression: Assign) -> object:
        """Define la operación sobre el destino y valor de una asignación."""
        raise NotImplementedError()

    def visit_var_decl(self, statement: VarDecl) -> object:
        """Define la operación sobre una declaración var con valor opcional."""
        raise NotImplementedError()

    def visit_block_stmt(self, statement: BlockStmt) -> object:
        """Define la operación sobre una lista de nodos encerrada entre llaves."""
        raise NotImplementedError()

    def visit_if_stmt(self, statement: IfStmt) -> object:
        """Define la operación sobre una condición y las ramas de un if."""
        raise NotImplementedError()

    def visit_while_stmt(self, statement: WhileStmt) -> object:
        """Define la operación sobre una condición y el cuerpo de un bucle."""
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
    """Representa una expresión terminada por punto y coma, como ``x = 2;``.

    ``expression`` guarda el cálculo o asignación. Al ejecutar esta sentencia,
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


@dataclass(frozen=True, slots=True)
class Variable(Node):
    """Referencia a una variable usada como expresión, por ejemplo ``x``.

    ``name`` guarda el token del identificador, no el valor de la variable.
    El intérprete consulta su ambiente al ejecutar esta referencia.
    """
    name: Token

    def accept(self, visitor: Visitor) -> object:
        """Selecciona ``visit_variable`` para visitar la referencia al nombre."""
        return visitor.visit_variable(self)


@dataclass(frozen=True, slots=True)
class Assign(Node):
    """Expresión de asignación a un nombre, como ``x = x + 1``.

    ``name`` identifica el destino y ``value`` es el subárbol que produce
    el nuevo valor. La ejecución devuelve ese valor, lo que permite que
    otra asignación o expresión contenga este nodo.
    """
    name: Token
    value: Node

    def accept(self, visitor: Visitor) -> object:
        """Selecciona ``visit_assign`` para visitar el destino y su expresión."""
        return visitor.visit_assign(self)


@dataclass(frozen=True, slots=True)
class VarDecl(Node):
    """Declaración de variable con nombre e inicializador opcional.

    ``initializer = None`` significa que no se escribió un inicializador;
    Interpreter usará nil. Esto se distingue de Literal(None), que representa
    la expresión explícita de ``var x = nil;``.
    """
    name: Token
    initializer: Node | None

    def accept(self, visitor: Visitor) -> object:
        """Selecciona ``visit_var_decl`` para visitar la declaración completa."""
        return visitor.visit_var_decl(self)


@dataclass(frozen=True, slots=True)
class BlockStmt(Node):
    """Lista de declaraciones y sentencias agrupadas entre llaves.

    ``statements`` conserva el orden del cuerpo y puede estar vacía.
    Interpreter ejecuta esta lista en un ámbito propio; el parser también
    usa bloques al transformar un for en un while con inicio e incremento.
    """
    statements: list[Node]

    def accept(self, visitor: Visitor) -> object:
        """Selecciona ``visit_block_stmt`` para visitar el cuerpo del bloque."""
        return visitor.visit_block_stmt(self)


@dataclass(frozen=True, slots=True)
class IfStmt(Node):
    """Selección entre una rama verdadera y una rama else opcional.

    ``condition`` es una expresión. Cada rama es una sentencia, que puede
    ser un bloque o un if anidado. ``else_branch = None`` indica que la
    fuente no incluyó else; ambas ramas se conservan sin evaluarlas aquí.
    """
    condition: Node
    then_branch: Node
    else_branch: Node | None

    def accept(self, visitor: Visitor) -> object:
        """Selecciona ``visit_if_stmt`` para visitar la condición y sus ramas."""
        return visitor.visit_if_stmt(self)


@dataclass(frozen=True, slots=True)
class WhileStmt(Node):
    """Bucle con una condición que precede a cada ejecución de su cuerpo.

    ``condition`` guarda el AST que el intérprete reevalúa en cada vuelta;
    ``body`` es una sentencia o bloque. También representa el bucle generado
    por el parser al transformar una sentencia for.
    """
    condition: Node
    body: Node

    def accept(self, visitor: Visitor) -> object:
        """Selecciona ``visit_while_stmt`` para visitar la estructura del bucle."""
        return visitor.visit_while_stmt(self)
