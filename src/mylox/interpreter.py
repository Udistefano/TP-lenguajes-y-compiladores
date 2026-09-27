from __future__ import annotations

from .errors import LoxRuntimeError
from .nodes import Binary, Call, Grouping, Literal, Node, Unary, Visitor
from .tokens import Token, TokenKind


class Interpreter(Visitor):
    """
    Convierte nodos del arbol en valores de Lox recorriendo el tree-walk interpreter
    """

    def evaluate(self, expression: Node) -> object:
        """Evalúa una expresión y devuelve el valor resultante."""
        return expression.accept(self)

    # helpers

    def is_number(self, value: object) -> bool:
        return isinstance(value, float)

    def is_string(self, value: object) -> bool:
        return isinstance(value, str)

    def is_truthy(self, value: object) -> bool:
        """En Lox, `nil` y `false` son falsy; el resto (incluido 0) es truthy."""
        return not (value is None or value is False)

    def is_callable(self, value: object) -> bool:
        """Devuelve si el valor es invocable como una función o clase."""
        return hasattr(value, "arity") and hasattr(value, "call")

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