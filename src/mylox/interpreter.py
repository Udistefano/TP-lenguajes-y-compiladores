from __future__ import annotations

from .errors import LoxRuntimeError
from .nodes import Binary, ExprStmt, Grouping, Literal, Node, PrintStmt, Unary, Visitor
from .tokens import Token, TokenKind


class Interpreter(Visitor):
    """
    Convierte nodos del arbol en valores de Lox recorriendo el tree-walk interpreter
    """

    def evaluate(self, expression: Node) -> object:
        """Evalúa una expresión y devuelve el valor resultante."""
        return expression.accept(self)

    def interpret(self, statements: list[Node]) -> None:
        """Ejecuta las sentencias del programa en orden mediante accept(self).

        Descarta el resultado de cada sentencia y devuelve None al terminar.
        Una lista vacía no realiza acciones. Si una sentencia lanza una
        excepción, la propaga y no ejecuta las sentencias siguientes.
        """
        for statement in statements:
            statement.accept(self)

    def visit_expr_stmt(self, statement: ExprStmt) -> None:
        """Evalúa una expresión usada como sentencia y descarta su valor.

        Por ejemplo, 2 + 3; calcula 5 sin imprimirlo. Los errores de la
        expresión se propagan y la sentencia devuelve None.
        """
        self.evaluate(statement.expression)

    def visit_print_stmt(self, statement: PrintStmt) -> None:
        """Evalúa la expresión de ``print`` y escribe su valor en stdout.

        ``stringify()`` aplica el formato de Lox, como ``nil`` y ``true``,
        y ``print()`` agrega el salto de línea. La expresión se evalúa una
        sola vez; la sentencia produce ese efecto y devuelve None.
        """
        print(self.stringify(self.evaluate(statement.expression)))

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