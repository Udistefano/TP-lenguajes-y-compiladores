from ..nodes import Node
from ..tokens import Token, TokenKind

# Toma la lista dondee tokens del lexer y la agrupa en el AST con expresiones y sentencias.
class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.current = 0

    def parse(self) -> Node:
        raise NotImplementedError("Parseo todavía no implementado")

    def _peek(self) -> Token:
        raise NotImplementedError("_peek todavía no implementado")

    def _previous(self) -> Token:
        raise NotImplementedError("_previous todavía no implementado")

    def _advance(self) -> Token:
        raise NotImplementedError("_advance todavía no implementado")

    def _match(self, *kinds: TokenKind) -> bool:
        raise NotImplementedError("_match todavía no implementado")

    def _check(self, kind: TokenKind) -> bool:
        raise NotImplementedError("_check todavía no implementado")