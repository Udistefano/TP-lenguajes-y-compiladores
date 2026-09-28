"""Nodos del AST y contrato Visitor para recorrerlos con double dispatch.

Los nodos guardan estructura y tokens; no calculan valores ni modifican
ambientes. ``accept()`` selecciona el método del visitante correspondiente.
"""

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
        """Delega el nodo en el visitante y devuelve el resultado de la visita.

        Cada subclase debe seleccionar su método ``visit_*``. El resultado
        depende del visitante: puede ser un valor, texto o None. La clase
        base informa NotImplementedError si una subclase omite este contrato.
        """
        raise NotImplementedError(
            f"{type(self).__name__} no implementa accept()"
        )


class Visitor:
    """Contrato de las operaciones disponibles para cada forma de nodo.

    Un nodo elige aquí el método según su tipo y el visitante concreto
    implementa la operación. Interpreter ejecuta el AST e Impresor genera
    texto. Estos métodos base lanzan NotImplementedError si una operación
    no fue implementada por el visitante usado.
    """

    def visit_literal(self, expression: Literal) -> object:
        """Define la operación del visitante sobre un valor literal del AST."""
        raise NotImplementedError()

    def visit_unary(self, expression: Unary) -> object:
        """Define la operación sobre un prefijo y su único operando."""
        raise NotImplementedError()

    def visit_binary(self, expression: Binary) -> object:
        """Define la operación sobre dos operandos unidos por un operador."""
        raise NotImplementedError()

    def visit_grouping(self, expression: Grouping) -> object:
        """Define la operación sobre una expresión agrupada con paréntesis."""
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

    def visit_call(self, expression: Call) -> object:
        raise NotImplementedError()

    def visit_logical(self, expression: Logical) -> object:
        raise NotImplementedError()




@dataclass(frozen=True, slots=True)
class Literal(Node):
    """Valor constante de número, cadena, booleano o nil.

    ``value`` contiene su representación en Python; None corresponde a nil.
    El nodo no necesita hijos para representar ese valor.
    """

    value: float | str | bool | None

    def accept(self, visitor: Visitor) -> object:
        """Selecciona ``visit_literal`` y devuelve el resultado del visitante."""
        return visitor.visit_literal(self)


@dataclass(frozen=True, slots=True)
class Unary(Node):
    """Expresión con un operador prefijo y un operando, como ``-3``.

    ``operator`` conserva el token y su posición; ``operand`` contiene el
    nodo al que se aplica el operador y puede ser otra expresión unaria.
    """

    operator: Token
    operand: Node

    def accept(self, visitor: Visitor) -> object:
        """Selecciona ``visit_unary`` y devuelve el resultado del visitante."""
        return visitor.visit_unary(self)


@dataclass(frozen=True, slots=True)
class Binary(Node):
    """Expresión con dos operandos y un operador, como ``a + 1``.

    ``left`` y ``right`` son subárboles cuya disposición fija la precedencia
    y asociatividad decididas por el parser. ``operator`` guarda el token
    que el visitante usará para elegir la operación o ubicar un error.
    """

    left: Node
    operator: Token
    right: Node

    def accept(self, visitor: Visitor) -> object:
        """Selecciona ``visit_binary`` y devuelve el resultado del visitante."""
        return visitor.visit_binary(self)


@dataclass(frozen=True, slots=True)
class Grouping(Node):
    """Expresión agrupada entre paréntesis para fijar el orden del árbol.

    ``expression`` conserva el subárbol interior. Una agrupación no representa
    un bloque de sentencias ni introduce un ámbito de variables.
    """

    expression: Node

    def accept(self, visitor: Visitor) -> object:
        """Selecciona ``visit_grouping`` y devuelve el resultado del visitante."""
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


@dataclass(frozen=True, slots=True)
class Call(Node):
    """llamada a una función o a una clase callable"""

    callee: Node
    paren: Token
    arguments: list[Node]

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_call(self)


@dataclass(frozen=True, slots=True)
class Logical(Node):
    """expresión lógica `and` / `or` con corto circuito."""

    left: Node
    operator: Token
    right: Node

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_logical(self)
