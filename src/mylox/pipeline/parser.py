from __future__ import annotations

from ..errors import ParseError
from ..nodes import Binary, ExprStmt, Grouping, Literal, Node, PrintStmt, Unary
from ..tokens import Token, TokenKind

class Parser:
    """
    Convierte secuencia de tokens en un árbol de expresiones AST

    El parser recorre las reglas de menor a mayor prioridad, construyendo el árbol de manera descendente y recursiva.
    """

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.current = 0

    def parse(self) -> list[Node]:
        """Construye todas las sentencias del programa hasta encontrar EOF.

        Cada vuelta agrega un nodo producido por _statement(). Un programa
        vacío devuelve una lista vacía. Los errores de sintaxis se propagan
        también después de una sentencia válida; no se devuelve un AST parcial.
        """
        statements: list[Node] = []
        while not self._check(TokenKind.EOF):
            statements.append(self._statement())
        return statements

    def _statement(self) -> Node:
        """Construye una sentencia print o una sentencia de expresión.

        Si encuentra PRINT, consume la palabra y construye su expresión.
        En otro caso lee una expresión ordinaria. Ambas formas exigen un
        punto y coma final y devuelven su nodo sin ejecutar la sentencia.
        """
        if self._match(TokenKind.PRINT):
            expression = self._expression()
            self._consume(TokenKind.SEMICOLON, "Se esperaba ';' después de print")
            return PrintStmt(expression)
        expression = self._expression()
        self._consume(TokenKind.SEMICOLON, "Se esperaba ';' después de la expresión")
        return ExprStmt(expression)

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

    def _consume(self, kind: TokenKind, message: str) -> Token:
        """Exige un tipo de token y lo consume, o informa un error de sintaxis.

        Si coincide, devuelve el Token y avanza. Si no coincide, lanza
        ParseError con ``message``, el lexema encontrado y su línea y columna.
        El llamador usa este método para nombres y delimitadores obligatorios.
        """
        if self._check(kind):
            return self._advance()
        token = self._peek()
        raise ParseError(
            f"{message}, se encontró {token.lexeme!r} "
            f"en la línea {token.line}, columna {token.column}"
        )
