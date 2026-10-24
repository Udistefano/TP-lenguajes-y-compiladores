"""Compilador de Lox a bytecode, de una sola pasada"""
from __future__ import annotations

from ..errors import ParseError
from ..tokens import Token, TokenKind
from .chunk import Chunk
from .opcodes import OpCode


class Compiler:
    """Traduce una secuencia de tokens en un chunk de bytecode.
    """

    def __init__(self, tokens: list[Token]) -> None:
        """Conserva la secuencia de tokens e inicia el cursor y el chunk."""
        self.tokens = tokens
        self.current = 0
        self.chunk = Chunk()

    def compile(self) -> Chunk:
        """Compila una expresión completa y devuelve el chunk resultante."""
        self.expression()
        if not self.is_at_end():
            token = self.peek()
            raise ParseError(
                f"Se esperaba fin de archivo, se encontró {token.lexeme!r} "
                f"en la línea {token.line}, columna {token.column}"
            )
        self.chunk.emit(OpCode.OP_RETURN, self.previous().line)
        return self.chunk

    # Reglas 

    def expression(self) -> None:
        """expression → equality"""
        self.equality()

    def equality(self) -> None:
        """equality → comparison ( ( '!=' | '==' ) comparison )*"""
        self.comparison()
        while self.match(TokenKind.BANG_EQUAL, TokenKind.EQUAL_EQUAL):
            operator = self.previous()
            self.comparison()
            if operator.kind == TokenKind.BANG_EQUAL:
                self.chunk.emit(OpCode.OP_EQUAL, operator.line)
                self.chunk.emit(OpCode.OP_NOT, operator.line)
            else:
                self.chunk.emit(OpCode.OP_EQUAL, operator.line)

    def comparison(self) -> None:
        """comparison → term ( ( '>' | '>=' | '<' | '<=' ) term )*"""
        self.term()
        while self.match(
            TokenKind.GREATER, TokenKind.GREATER_EQUAL,
            TokenKind.LESS, TokenKind.LESS_EQUAL,
        ):
            operator = self.previous()
            self.term()
            if operator.kind == TokenKind.GREATER:
                self.chunk.emit(OpCode.OP_GREATER, operator.line)
            elif operator.kind == TokenKind.GREATER_EQUAL:
                # a >= b  ⇔  !(a < b)
                self.chunk.emit(OpCode.OP_LESS, operator.line)
                self.chunk.emit(OpCode.OP_NOT, operator.line)
            elif operator.kind == TokenKind.LESS:
                self.chunk.emit(OpCode.OP_LESS, operator.line)
            else:  # LESS_EQUAL
                # a <= b  ⇔  !(a > b)
                self.chunk.emit(OpCode.OP_GREATER, operator.line)
                self.chunk.emit(OpCode.OP_NOT, operator.line)

    def term(self) -> None:
        """term → factor ( ( '-' | '+' ) factor )*"""
        self.factor()
        while self.match(TokenKind.MINUS, TokenKind.PLUS):
            operator = self.previous()
            self.factor()
            if operator.kind == TokenKind.MINUS:
                self.chunk.emit(OpCode.OP_SUBTRACT, operator.line)
            else:
                self.chunk.emit(OpCode.OP_ADD, operator.line)

    def factor(self) -> None:
        """factor → unary ( ( '/' | '*' | '%' ) unary )*"""
        self.unary()
        while self.match(TokenKind.SLASH, TokenKind.STAR, TokenKind.PERCENT):
            operator = self.previous()
            self.unary()
            if operator.kind == TokenKind.SLASH:
                self.chunk.emit(OpCode.OP_DIVIDE, operator.line)
            elif operator.kind == TokenKind.PERCENT:
                self.chunk.emit(OpCode.OP_MODULO, operator.line)
            else:
                self.chunk.emit(OpCode.OP_MULTIPLY, operator.line)

    def unary(self) -> None:
        """unary → ( '!' | '-' ) unary | primary"""
        if self.match(TokenKind.BANG, TokenKind.MINUS):
            operator = self.previous()
            self.unary()
            if operator.kind == TokenKind.BANG:
                self.chunk.emit(OpCode.OP_NOT, operator.line)
            else:
                self.chunk.emit(OpCode.OP_NEGATE, operator.line)
        else:
            self.primary()

    def primary(self) -> None:
        """primary → NUMBER | STRING | true | false | nil | '(' expression ')'"""
        if self.match(TokenKind.FALSE):
            self.chunk.emit(OpCode.OP_FALSE, self.previous().line)
            return
        if self.match(TokenKind.TRUE):
            self.chunk.emit(OpCode.OP_TRUE, self.previous().line)
            return
        if self.match(TokenKind.NIL):
            self.chunk.emit(OpCode.OP_NIL, self.previous().line)
            return
        if self.match(TokenKind.NUMBER, TokenKind.STRING):
            token = self.previous()
            self.chunk.emit(
                OpCode.OP_CONSTANT, token.line, self.chunk.add_constant(token.literal)
            )
            return
        if self.match(TokenKind.LEFT_PAREN):
            self.expression()
            if not self.match(TokenKind.RIGHT_PAREN):
                token = self.peek()
                raise ParseError(
                    f"Se esperaba ')' después de la expresión, "
                    f"se encontró {token.lexeme!r} en la línea {token.line}, "
                    f"columna {token.column}"
                )
            return

        token = self.peek()
        raise ParseError(
            f"Se esperaba una expresión, se encontró {token.lexeme!r} "
            f"en la línea {token.line}, columna {token.column}"
        )

    #Tokens 

    def is_at_end(self) -> bool:
        """Indica si el cursor llegó al token EOF."""
        return self.peek().kind == TokenKind.EOF

    def peek(self) -> Token:
        """Devuelve el token actual sin consumirlo."""
        return self.tokens[self.current]

    def previous(self) -> Token:
        """Devuelve el último token consumido."""
        return self.tokens[self.current - 1]

    def advance(self) -> Token:
        """Consume el token actual y lo devuelve."""
        if not self.is_at_end():
            self.current += 1
        return self.previous()

    def match(self, *kinds: TokenKind) -> bool:
        """Consume el token actual si es alguno de los tipos pedidos."""
        for kind in kinds:
            if self.check(kind):
                self.advance()
                return True
        return False

    def check(self, kind: TokenKind) -> bool:
        """Indica si el token actual es del tipo pedido."""
        if self.is_at_end():
            return False
        return self.peek().kind == kind
