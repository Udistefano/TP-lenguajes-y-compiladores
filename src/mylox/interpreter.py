from __future__ import annotations

from .env import Env
from .errors import LoxRuntimeError
from .nodes import (
    Assign, Binary, BlockStmt, ExprStmt, Grouping, Literal, Node,
    PrintStmt, Unary, VarDecl, Variable, Visitor,
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
        """Evalúa una expresión y devuelve el valor resultante."""
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
        return isinstance(value, float)

    def is_string(self, value: object) -> bool:
        return isinstance(value, str)

    def is_truthy(self, value: object) -> bool:
        """En Lox, `nil` y `false` son falsy; el resto (incluido 0) es truthy."""
        return not (value is None or value is False)

    def check_number_operands(self, operator: Token, left: object, right: object) -> None:
        if not (self.is_number(left) and self.is_number(right)):
            raise LoxRuntimeError(
                operator, "Operands of " + operator.lexeme + " must be numbers"
            )

    def check_plus_operands(self, operator: Token, left: object, right: object) -> None:
        if not (
            (self.is_number(left) and self.is_number(right)) or (self.is_string(left) and self.is_string(right))
        ):
            raise LoxRuntimeError(
                operator,
                "Operands of " + operator.lexeme + " must be two numbers or two strings",
            )

    def visit_literal(self, expression: Literal) -> object:
        return expression.value

    def visit_grouping(self, expression: Grouping) -> object:
        return self.evaluate(expression.expression)

    def visit_unary(self, expression: Unary) -> object:
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
            expression.operator,"Unknown unary operator " + expression.operator.lexeme,
        )

    def visit_binary(self, expression: Binary) -> object:
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