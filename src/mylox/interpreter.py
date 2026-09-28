"""Ejecución del AST de Lox mediante Visitor con double dispatch.

El parser ya decidió la estructura del programa. Este módulo recorre esos
nodos, calcula valores, modifica ambientes y realiza los efectos de las
sentencias. Una expresión devuelve un valor; una sentencia devuelve None.
"""

from __future__ import annotations

from .env import Env
from .errors import LoxRuntimeError
from .nodes import (
    Assign, Binary, BlockStmt, Call, ExprStmt, Grouping, IfStmt,
    Literal, Logical, Node, PrintStmt, Unary, VarDecl, Variable,
    Visitor, WhileStmt,
)
from .tokens import Token, TokenKind


class Interpreter(Visitor):
    """Visitante que evalúa expresiones y ejecuta sentencias en orden.

    ``globals`` conserva las variables del nivel superior y ``environment``
    apunta al ámbito activo. Cada nodo selecciona su método ``visit_*`` en
    ``accept()``; este visitante determina qué significa ejecutar ese nodo.
    La misma instancia puede ejecutar varios programas conservando sus globals.
    """

    def __init__(self) -> None:
        """Crea el ambiente global vacío y lo establece como ámbito activo.

        Al entrar en un bloque cambiará ``environment``, mientras que
        ``globals`` seguirá apuntando al ambiente del nivel superior.
        """
        self.globals = Env()
        self.environment = self.globals

    def evaluate(self, expression: Node) -> object:
        """Obtiene el valor de una expresión delegando en su ``accept()``.

        El nodo llama al ``visit_*`` correspondiente y ese método puede
        evaluar otros nodos recursivamente. El resultado es un valor de Lox
        representado en Python; los errores de evaluación se propagan.
        """
        return expression.accept(self)

    def interpret(self, statements: list[Node]) -> None:
        """Ejecuta la lista del programa en orden usando el ambiente activo.

        Cada sentencia se despacha con ``accept(self)`` y su resultado se
        descarta. Una lista vacía no realiza acciones. Si una sentencia lanza
        una excepción, se propaga y las sentencias siguientes no se ejecutan.
        """
        for statement in statements:
            statement.accept(self)

    def execute_block(self, statements: list[Node], environment: Env) -> None:
        """Ejecuta una lista de sentencias dentro del ambiente recibido.

        Guarda el ámbito activo, cambia a ``environment`` y ejecuta el cuerpo.
        El ``finally`` restaura el ámbito anterior tanto al terminar normalmente
        como al propagarse una excepción. El llamador crea el ambiente: un
        bloque lo encadena al actual y una función podrá encadenarlo a su closure.
        Este método devuelve None y permite que las excepciones salgan del cuerpo.
        """
        previous = self.environment
        self.environment = environment
        try:
            self.interpret(statements)
        finally:
            self.environment = previous

    def visit_expr_stmt(self, statement: ExprStmt) -> None:
        """Evalúa la expresión de una sentencia y descarta su valor.

        Por ejemplo, ``x = x + 1;`` conserva el efecto de la asignación, pero
        no imprime el valor devuelto por ella. Los errores de la expresión
        se propagan; la sentencia devuelve None.
        """
        self.evaluate(statement.expression)

    def visit_print_stmt(self, statement: PrintStmt) -> None:
        """Evalúa la expresión de ``print`` y escribe su valor en stdout.

        ``stringify()`` aplica el formato de Lox, como ``nil`` y ``true``,
        y ``print()`` agrega el salto de línea. La expresión se evalúa una
        sola vez; la sentencia produce ese efecto y devuelve None.
        """
        print(self.stringify(self.evaluate(statement.expression)))

    def visit_var_decl(self, statement: VarDecl) -> None:
        """Declara el nombre de ``var`` en el ámbito activo y devuelve None.

        Primero evalúa el inicializador, si existe; en su ausencia usa None,
        que representa ``nil``. Luego define el nombre en el ambiente actual.
        Esto puede sombrear una variable exterior o reemplazar una declaración
        del mismo ámbito. Si el inicializador falla, no se define el nombre.
        """
        value = (
            self.evaluate(statement.initializer)
            if statement.initializer is not None else None
        )
        self.environment.define(statement.name.lexeme, value)

    def visit_variable(self, expression: Variable) -> object:
        """Devuelve el valor asociado al nombre de una expresión Variable.

        ``Env.get()`` busca primero en el ámbito activo y después en sus padres.
        Si el nombre no existe en toda la cadena, propaga LoxRuntimeError con
        el token de la referencia para señalar su posición en el programa.
        """
        return self.environment.get(expression.name)

    def visit_assign(self, expression: Assign) -> object:
        """Evalúa el nuevo valor, actualiza una variable existente y lo devuelve.

        ``Env.assign()`` modifica el primer ámbito de la cadena que contiene
        el nombre; no crea una variable nueva. Devolver el valor permite
        asignaciones encadenadas como ``a = b = 3``. Un nombre indefinido
        produce LoxRuntimeError después de evaluar la expresión derecha.
        """
        value = self.evaluate(expression.value)
        self.environment.assign(expression.name, value)
        return value

    def visit_block_stmt(self, statement: BlockStmt) -> None:
        """Ejecuta las sentencias entre llaves en un ámbito nuevo y devuelve None.

        El padre del ambiente nuevo es el ámbito activo, de modo que el cuerpo
        puede leer o modificar nombres exteriores. Sus declaraciones quedan
        en el ambiente local. ``execute_block()`` restaura el ámbito anterior
        incluso si una sentencia del cuerpo falla.
        """
        self.execute_block(statement.statements, Env(enclosing=self.environment))



    def visit_if_stmt(self, statement: IfStmt) -> None:
        """Evalúa la condición de ``if`` y ejecuta solamente la rama elegida.

        Si ``is_truthy()`` considera verdadero el valor, ejecuta ``then_branch``.
        En caso contrario ejecuta ``else_branch`` si está presente. La condición
        se evalúa una sola vez; los errores de la rama elegida se propagan y
        la sentencia devuelve None.
        """
        if self.is_truthy(self.evaluate(statement.condition)):
            statement.then_branch.accept(self)
        elif statement.else_branch is not None:
            statement.else_branch.accept(self)

    def visit_while_stmt(self, statement: WhileStmt) -> None:
        """Repite el cuerpo de ``while`` mientras la condición sea verdadera.

        Reevalúa el AST de la condición antes de cada vuelta para observar los
        valores actualizados por el cuerpo. Si empieza siendo falsa, el cuerpo
        no se ejecuta. También ejecuta los ``for`` que el parser transformó
        en WhileStmt. Devuelve None al terminar y propaga errores del cuerpo.
        """
        while self.is_truthy(self.evaluate(statement.condition)):
            statement.body.accept(self)

    def stringify(self, value: object) -> str:
        """Convierte un valor ya evaluado a su representación textual en Lox.

        None se escribe ``nil`` y los booleanos se escriben en minúscula.
        Los números enteros almacenados como float se muestran sin ``.0``;
        las cadenas se muestran sin comillas. Devuelve texto sin imprimirlo
        ni agregar un salto de línea.
        """
        if value is None:
            return "nil"
        if value is True:
            return "true"
        if value is False:
            return "false"
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    # helpers

    def is_number(self, value: object) -> bool:
        """Indica si el valor usa la representación numérica float de Lox.

        El lexer convierte todos los literales numéricos a float. Comprobar
        ese tipo evita tratar los booleanos de Python como números.
        """
        return isinstance(value, float)

    def is_string(self, value: object) -> bool:
        """Indica si el valor es una cadena de Lox, representada por str.

        Se usa al validar la concatenación con ``+`` y no convierte valores
        de otros tipos a texto automáticamente.
        """
        return isinstance(value, str)

    def is_truthy(self, value: object) -> bool:
        """Devuelve la interpretación de un valor como condición de Lox.

        Solamente None (``nil``) y False se consideran falsos. El cero y la
        cadena vacía son verdaderos. Usar esta regla evita las diferencias
        con ``bool()`` de Python al ejecutar ``if``, ``while`` o ``!``.
        """
        return not (value is None or value is False)

    def is_callable(self, value: object) -> bool:
        """Devuelve si el valor es invocable como una función o clase."""
        return hasattr(value, "arity") and hasattr(value, "call")

    def check_number_operands(self, operator: Token, left: object, right: object) -> None:
        """Exige que los dos operandos ya evaluados sean números de Lox.

        Se usa en operaciones aritméticas y comparaciones de orden. Si ambos
        son válidos devuelve None; en otro caso lanza LoxRuntimeError usando
        el token del operador para conservar la ubicación del error.
        """
        if not (self.is_number(left) and self.is_number(right)):
            raise LoxRuntimeError(
                operator, "Operands of " + operator.lexeme + " must be numbers"
            )

    def check_plus_operands(self, operator: Token, left: object, right: object) -> None:
        """Valida que ``+`` reciba dos números o dos cadenas.

        La operación suma números o concatena cadenas; mezclar los tipos
        requiere un error y no una conversión implícita. Devuelve None si
        el par es válido y lanza LoxRuntimeError con el operador si no lo es.
        """
        if not (
            (self.is_number(left) and self.is_number(right)) or (self.is_string(left) and self.is_string(right))
        ):
            raise LoxRuntimeError(
                operator,
                "Operands of " + operator.lexeme + " must be two numbers or two strings",
            )

    def visit_literal(self, expression: Literal) -> object:
        """Devuelve el valor que el nodo Literal ya almacena en Python.

        Los números y las cadenas fueron convertidos por el lexer, y el parser
        construyó los valores de ``true``, ``false`` y ``nil``. Un literal no
        necesita evaluar otros nodos ni consultar el ambiente.
        """
        return expression.value

    def visit_grouping(self, expression: Grouping) -> object:
        """Evalúa la expresión entre paréntesis y devuelve su mismo valor.

        El parser ya usó los paréntesis para fijar la agrupación del AST.
        Durante la ejecución basta con delegar en el nodo interior; agrupar
        una expresión no crea un ámbito nuevo.
        """
        return self.evaluate(expression.expression)

    def visit_unary(self, expression: Unary) -> object:
        """Evalúa el operando una vez y aplica ``-`` o ``!``.

        ``-`` exige un número y devuelve su negación. ``!`` acepta cualquier
        valor y devuelve el booleano contrario a ``is_truthy()``. Un tipo
        incompatible con ``-`` o un operador desconocido produce
        LoxRuntimeError asociado al token del operador.
        """
        right = self.evaluate(expression.operand)

        #Se utiliza match case como en el libro de lox para manejar los diferentes operadores unarios
        match expression.operator.kind:
            case TokenKind.MINUS:
                if not self.is_number(right):
                    raise LoxRuntimeError(
                        expression.operator, "Operand of - must be a number"
                    )
                return -right
            case TokenKind.BANG:
                return not self.is_truthy(right)

        raise LoxRuntimeError(
            expression.operator, "Unknown unary operator " + expression.operator.lexeme,
        )

    def visit_call(self, expression: Call) -> object:
        """Evalúa el callable y sus argumentos, valida la aridad e invoca."""

        callee = self.evaluate(expression.callee)

        if not self.is_callable(callee):
            raise LoxRuntimeError(
                expression.paren, "Can only call functions and classes."
            )

        arguments = [self.evaluate(argument) for argument in expression.arguments]

        if len(arguments) != callee.arity:
            raise LoxRuntimeError(
                expression.paren,
                "Expected " + str(callee.arity) + " arguments but got " + str(len(arguments)) + ".",
            )

        return callee.call(self, arguments)

    def visit_logical(self, expression: Logical) -> object:
        """Evalúa `and`/`or` con corto circuito, devolviendo operandos, no bools."""

        left = self.evaluate(expression.left)

        if expression.operator.kind == TokenKind.OR and self.is_truthy(left):
            return left

        if expression.operator.kind == TokenKind.AND and not self.is_truthy(left):
            return left

        return self.evaluate(expression.right)

    def visit_binary(self, expression: Binary) -> object:
        """Evalúa izquierda y derecha, en ese orden, y aplica el operador.

        ``+`` suma números o concatena cadenas. Los demás operadores
        aritméticos y las comparaciones de orden exigen números. ``==`` y
        ``!=`` comparan los valores evaluados y devuelven un booleano.
        Los validadores rechazan tipos incompatibles con LoxRuntimeError;
        un operador no reconocido también produce ese error. El resultado
        se devuelve a la expresión o sentencia que contiene este nodo.
        """
        left = self.evaluate(expression.left)
        right = self.evaluate(expression.right)

        #Se utiliza match case como en el libro de lox para manejar los diferentes operadores binarios
        match expression.operator.kind:
            case TokenKind.PLUS:
                self.check_plus_operands(expression.operator, left, right)
                return left + right
            case TokenKind.MINUS:
                self.check_number_operands(expression.operator, left, right)
                return left - right
            case TokenKind.STAR:
                self.check_number_operands(expression.operator, left, right)
                return left * right
            case TokenKind.SLASH:
                self.check_number_operands(expression.operator, left, right)
                return left / right
            case TokenKind.PERCENT:
                self.check_number_operands(expression.operator, left, right)
                return left % right
            case TokenKind.GREATER:
                self.check_number_operands(expression.operator, left, right)
                return left > right
            case TokenKind.GREATER_EQUAL:
                self.check_number_operands(expression.operator, left, right)
                return left >= right
            case TokenKind.LESS:
                self.check_number_operands(expression.operator, left, right)
                return left < right
            case TokenKind.LESS_EQUAL:
                self.check_number_operands(expression.operator, left, right)
                return left <= right
            case TokenKind.EQUAL_EQUAL:
                return left == right
            case TokenKind.BANG_EQUAL:
                return left != right

        raise LoxRuntimeError(
            expression.operator, "Unknown binary operator " + expression.operator.lexeme,
        )
