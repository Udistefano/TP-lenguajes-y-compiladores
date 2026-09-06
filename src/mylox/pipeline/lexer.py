from ..tokens import Token

# Toma el texto crudo que escribe el usuario y lo convierte en una lista de tokens (palabras con significado). 
# No entiende el sentido de la frase, solo separa las piezas.
"""
Cada token es una pieza con forma (kind) y texto crudo (lexeme):

1 → Token(TokenKind.NUMBER, "1", 1.0)
+ → Token(TokenKind.PLUS, "+", None)
2 → Token(TokenKind.NUMBER, "2", 2.0)
fin → Token(TokenKind.EOF, "", None)
"""
# FALTA LOGICA DEL LEXER, SOLO SE DECLARAN LOS METODOS Y ATRIBUTOS.
class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.tokens = []
        self.start = 0
        self.current = 0

    def run(self) -> list[Token]:
        raise NotImplementedError("Escaneo todavía no implementado")

    def _peek(self):
        raise NotImplementedError("_peek todavía no implementado")

    def _advance(self):
        raise NotImplementedError("_advance todavía no implementado")

    def _match(self, expected: str) -> bool:
        raise NotImplementedError("_match todavía no implementado")

    def _add(self, kind, literal=None):
        raise NotImplementedError("_add todavía no implementado")