"""Conversión del código fuente de Lox en una secuencia de tokens.

Cada token es una pieza con forma (kind) y texto crudo (lexeme):

1 → Token(TokenKind.NUMBER, "1", 1.0)
+ → Token(TokenKind.PLUS, "+", None)
2 → Token(TokenKind.NUMBER, "2", 2.0)
fin → Token(TokenKind.EOF, "", None)
"""


from ..errors import ScanError
from ..tokens import KEYWORDS, LiteralValue, Token, TokenKind


class Lexer:
    """Separa el código fuente en las unidades léxicas definidas por Lox.

    El lexer reconoce las palabras y símbolos válidos, pero no determina si
    estos forman expresiones o sentencias sintácticamente correctas.
    """

    SINGLE_CHARACTER_TOKENS: dict[str, TokenKind] = {
        "(": TokenKind.LEFT_PAREN,
        ")": TokenKind.RIGHT_PAREN,
        "{": TokenKind.LEFT_BRACE,
        "}": TokenKind.RIGHT_BRACE,
        ",": TokenKind.COMMA,
        ".": TokenKind.DOT,
        "+": TokenKind.PLUS,
        "-": TokenKind.MINUS,
        "*": TokenKind.STAR,
        "%": TokenKind.PERCENT,
        ";": TokenKind.SEMICOLON,
    }

    def __init__(self, source: str) -> None:
        """Inicializa el recorrido al comienzo del código fuente recibido."""

        self.source = source
        self.tokens: list[Token] = []
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1

        # Posición inicial del token que se está reconociendo.
        self.token_line = 1
        self.token_column = 1

    def _scan_token(self) -> None:
        """Reconoce el token que comienza en la posición actual."""

        character = self._advance()  # consumo token. mueve puntero.

        if character in {" ", "\r", "\t", "\n"}:  # no son tokens; sino que separan.
            return

        if character == "/":
            # caso para comentarios.
            if self._match("/"):
                self._discard_comment()
            else:
                self._add(TokenKind.SLASH)

            return

        kind = self.SINGLE_CHARACTER_TOKENS.get(character)

        if kind is not None:
            self._add(kind)
            return

        raise ScanError(
            f"Carácter inesperado {character!r} "
            f"en la línea {self.token_line}, "
            f"columna {self.token_column}"
        )

    def _discard_comment(self) -> None:
        """Consume un comentario de línea sin incluir el salto final."""

        while self._peek() not in {"\n", "\0"}:
            self._advance()


    def run(self) -> list[Token]:
        """Escanea toda la fuente y devuelve los tokens, incluido EOF."""

        while not self._is_at_end():
            self.start = self.current
            self.token_line = self.line
            self.token_column = self.column

            self._scan_token()

        eof = Token(
            kind=TokenKind.EOF,
            lexeme="",
            line=self.line,
            column=self.column,
        )

        self.tokens.append(eof)
        return self.tokens

    def _is_at_end(self) -> bool:
        """Indica si el cursor alcanzó o superó el final de la fuente."""

        return self.current >= len(self.source)

    def _peek(self) -> str:
        """Devuelve el carácter actual sin consumirlo, o ``\0`` al final."""

        if self._is_at_end():
            return "\0"

        return self.source[self.current]

    def _peek_next(self) -> str:
        """Mira un carácter por delante sin modificar el cursor."""

        next_position = self.current + 1

        if next_position >= len(self.source):
            return "\0"

        return self.source[next_position]

    def _advance(self) -> str:
        """Consume el carácter actual y actualiza el cursor y su posición."""

        character = self.source[self.current]
        self.current += 1

        if character == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return character

    def _match(self, expected: str) -> bool:
        """Consume el carácter actual solo cuando coincide con ``expected``."""

        if self._is_at_end():
            return False

        if self.source[self.current] != expected:
            return False

        self._advance()
        return True

    def _add(
        self,
        kind: TokenKind,
        literal: LiteralValue = None,
    ) -> None:
        """Agrega un token usando el segmento actual y su posición inicial."""

        lexeme = self.source[self.start:self.current]

        token = Token(
            kind=kind,
            lexeme=lexeme,
            literal=literal,
            line=self.token_line,
            column=self.token_column,
        )

        self.tokens.append(token)
