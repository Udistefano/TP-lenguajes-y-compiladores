from enum import Enum, auto

#clase que representa los diferentes tipos de tokens que pueden aparecer en el código
# se usa auto() para asignar automáticamente valores únicos a cada miembro del enumerado.
class TokenKind(Enum):
    # Símbolos de un solo carácter
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

    # Fin de la entrada
    EOF = auto()


#clase que representa un token, que es una unidad léxica del código fuente. 
# Cada token tiene un tipo kind, un lexeme y un valor Literal opcional.
class Token:
    def __init__(self, kind, lexeme, literal=None):
        self.kind = kind
        self.lexeme = lexeme
        self.literal = literal

    def __str__(self):
        if self.literal is not None:
            return f"{self.kind.name}<{self.literal}>"
        return self.kind.name


KEYWORDS = {
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