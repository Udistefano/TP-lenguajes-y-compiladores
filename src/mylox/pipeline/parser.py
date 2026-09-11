from __future__ import annotations

from ..errors import ParseError
from ..nodes import Binary, Grouping, Literal, Node, Unary
from ..tokens import Token, TokenKind

class Parser:
    """
    Convierte secuencia de tokens en un árbol de expresiones AST

    El parser recorre las reglas de menor a mayor prioridad, construyendo el árbol de manera descendente y recursiva.
    """

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.current = 0

    def parse(self) -> Node:
        """Construye el árbol de la expresión completa."""
        return self._expression()

    # Reglas de producción 

    def _expression(self) -> Node:
        """expression → equality"""

        return self._equality()

    def _equality(self) -> Node:
        """equality → comparison ( ( "!=" | "==" ) comparison )*"""

        expression = self._comparison()

        while self._match(TokenKind.BANG_EQUAL, TokenKind.EQUAL_EQUAL):
            operator = self._previous()
            right = self._comparison()
            expression = Binary(expression, operator, right)

        return expression

    def _comparison(self) -> Node:
        """comparison → term ( ( ">" | ">=" | "<" | "<=" ) term )*"""

        expression = self._term()

        while self._match(
            TokenKind.GREATER,
            TokenKind.GREATER_EQUAL,
            TokenKind.LESS,
            TokenKind.LESS_EQUAL,
        ):
            operator = self._previous()
            right = self._term()
            expression = Binary(expression, operator, right)

        return expression

    def _term(self) -> Node:
        """term → factor ( ( "-" | "+" ) factor )*"""

        expression = self._factor()

        while self._match(TokenKind.MINUS, TokenKind.PLUS):
            operator = self._previous()
            right = self._factor()
            expression = Binary(expression, operator, right)

        return expression

    def _factor(self) -> Node:
        """factor → unary ( ( "/" | "*" ) unary )*"""

        expression = self._unary()

        while self._match(TokenKind.SLASH, TokenKind.STAR):
            operator = self._previous()
            right = self._unary()
            expression = Binary(expression, operator, right)

        return expression

    def _unary(self) -> Node:
        """unary → ( "!" | "-" ) unary | primary"""

        if self._match(TokenKind.BANG, TokenKind.MINUS):
            operator = self._previous()
            right = self._unary()
            return Unary(operator, right)

        return self._primary()

    def _primary(self) -> Node:
        """primary → NUMBER | STRING | "true" | "false" | "nil" | "(" expression ")" """

        if self._match(TokenKind.FALSE):
            return Literal(False)

        if self._match(TokenKind.TRUE):
            return Literal(True)

        if self._match(TokenKind.NIL):
            return Literal(None)

        if self._match(TokenKind.NUMBER, TokenKind.STRING):
            return Literal(self._previous().literal)

        if self._match(TokenKind.LEFT_PAREN):
            expression = self._expression()

            if not self._match(TokenKind.RIGHT_PAREN):
                token = self._peek()
                raise ParseError(
                    f"Se esperaba ')' después de la expresión, "
                    f"se encontró {token.lexeme!r} "
                    f"en la línea {token.line}, columna {token.column}"
                )

            return Grouping(expression)

        token = self._peek()
        raise ParseError(
            f"Se esperaba una expresión, "
            f"se encontró {token.lexeme!r} "
            f"en la línea {token.line}, columna {token.column}"
        )

    # Helpers 

    def _peek(self) -> Token:
        """Devuelve el token actual sin consumirlo."""

        return self.tokens[self.current]

    def _previous(self) -> Token:
        """Devuelve el último token consumido."""

        return self.tokens[self.current - 1]

    def _advance(self) -> Token:
        """Consume y devuelve el token actual."""

        token = self._peek()

        if token.kind is not TokenKind.EOF:
            self.current += 1

        return token

    def _match(self, *kinds: TokenKind) -> bool:
        """Consume el token actual si su tipo es alguno de ``kinds``."""

        for kind in kinds:
            if self._check(kind):
                self._advance()
                return True

        return False

    def _check(self, kind: TokenKind) -> bool:
        """Devuelve si el token actual es de tipo ``kind`` sin consumirlo."""

        return self._peek().kind is kind