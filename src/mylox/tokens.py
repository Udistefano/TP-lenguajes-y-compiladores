from dataclasses import dataclass
from enum import Enum, auto
from typing import TypeAlias


LiteralValue: TypeAlias = str | float | bool | None

class TokenKind(Enum):
    """
    Clase que representa los diferentes tipos de tokens que pueden aparecer en el código
    se usa auto() para asignar automáticamente valores únicos a cada miembro del enumerado.
    """

    # Tokens de un solo carácter
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACE = auto()
    RIGHT_BRACE = auto()
    COMMA = auto()
    DOT = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    SEMICOLON = auto()

    # Símbolos
    BANG = auto()
    BANG_EQUAL = auto()
    EQUAL = auto()
    EQUAL_EQUAL = auto()
    GREATER = auto()
    GREATER_EQUAL = auto()
    LESS = auto()
    LESS_EQUAL = auto()

    # Literales
    IDENTIFIER = auto()
    STRING = auto()
    NUMBER = auto()

    # Palabras reservadas
    AND = auto()
    CLASS = auto()
    ELSE = auto()
    FALSE = auto()
    FOR = auto()
    FUN = auto()
    IF = auto()
    NIL = auto()
    OR = auto()
    PRINT = auto()
    RETURN = auto()
    SUPER = auto()
    THIS = auto()
    TRUE = auto()
    VAR = auto()
    WHILE = auto()

    EOF = auto()


@dataclass(frozen=True, slots=True)
class Token:
    """
    Clase que representa un token; una unidad léxica del código fuente.
    La línea y la columna son posiciones basadas en 1 dentro del código fuente.

    Posiciones inician en 1 y se validan. Para errores más claros.
    """

    kind: TokenKind
    lexeme: str
    literal: LiteralValue = None
    line: int = 1
    column: int = 1

    def __post_init__(self) -> None:
        if self.line < 1 or self.column < 1:
            raise ValueError("La línea y la columna deben comenzar en 1")

    def __str__(self) -> str:
        if self.literal is not None:
            return f"{self.kind.name}<{self.literal}>"
        return self.kind.name


KEYWORDS: dict[str, TokenKind] = {
    "and": TokenKind.AND,
    "class": TokenKind.CLASS,
    "else": TokenKind.ELSE,
    "false": TokenKind.FALSE,
    "for": TokenKind.FOR,
    "fun": TokenKind.FUN,
    "if": TokenKind.IF,
    "nil": TokenKind.NIL,
    "or": TokenKind.OR,
    "print": TokenKind.PRINT,
    "return": TokenKind.RETURN,
    "super": TokenKind.SUPER,
    "this": TokenKind.THIS,
    "true": TokenKind.TRUE,
    "var": TokenKind.VAR,
    "while": TokenKind.WHILE,
}
