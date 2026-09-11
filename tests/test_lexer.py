import pytest

from mylox.errors import ScanError
from mylox.pipeline.lexer import Lexer
from mylox.tokens import TokenKind


def kinds(source: str) -> list[TokenKind]:
    return [token.kind for token in Lexer(source).run()]


def test_tokens_simples():
    assert kinds("(){}.,+-*%;") == [
        TokenKind.LEFT_PAREN,
        TokenKind.RIGHT_PAREN,
        TokenKind.LEFT_BRACE,
        TokenKind.RIGHT_BRACE,
        TokenKind.DOT,
        TokenKind.COMMA,
        TokenKind.PLUS,
        TokenKind.MINUS,
        TokenKind.STAR,
        TokenKind.PERCENT,
        TokenKind.SEMICOLON,
        TokenKind.EOF,
    ]


def test_slash_simple():
    assert kinds("8 / 2") == [
        TokenKind.NUMBER,
        TokenKind.SLASH,
        TokenKind.NUMBER,
        TokenKind.EOF,
    ]


def test_operadores_de_uno_o_dos_caracteres():
    assert kinds("! != = == < <= > >=") == [
        TokenKind.BANG,
        TokenKind.BANG_EQUAL,
        TokenKind.EQUAL,
        TokenKind.EQUAL_EQUAL,
        TokenKind.LESS,
        TokenKind.LESS_EQUAL,
        TokenKind.GREATER,
        TokenKind.GREATER_EQUAL,
        TokenKind.EOF,
    ]


def test_strings():
    tokens = Lexer('"hola" + "mundo"').run()
    assert tokens[0].kind is TokenKind.STRING
    assert tokens[0].literal == "hola"
    assert tokens[2].kind is TokenKind.STRING
    assert tokens[2].literal == "mundo"


def test_string_sin_cerrar():
    with pytest.raises(ScanError):
        Lexer('"hola').run()


def test_numeros_enteros_y_decimales():
    tokens = Lexer("12 1.5").run()
    assert [t.literal for t in tokens[:2]] == [12.0, 1.5]


def test_numero_punto_suelto_no_consume_el_punto():
    assert kinds("1. + 2") == [
        TokenKind.NUMBER,
        TokenKind.DOT,
        TokenKind.PLUS,
        TokenKind.NUMBER,
        TokenKind.EOF,
    ]


def test_identificadores_y_palabras_reservadas():
    assert kinds("var foo and") == [
        TokenKind.VAR,
        TokenKind.IDENTIFIER,
        TokenKind.AND,
        TokenKind.EOF,
    ]


def test_identificador_que_contiene_palabra_reservada():
    assert kinds("trueman") == [TokenKind.IDENTIFIER, TokenKind.EOF]


def test_identificador_con_guion_bajo():
    assert kinds("_x foo2") == [
        TokenKind.IDENTIFIER,
        TokenKind.IDENTIFIER,
        TokenKind.EOF,
    ]


def test_comentarios_ignorados():
    assert kinds("1 + 2 // comentario") == [
        TokenKind.NUMBER,
        TokenKind.PLUS,
        TokenKind.NUMBER,
        TokenKind.EOF,
    ]


def test_espacios_y_nueva_linea():
    assert kinds("1 + 2\n3") == [
        TokenKind.NUMBER,
        TokenKind.PLUS,
        TokenKind.NUMBER,
        TokenKind.NUMBER,
        TokenKind.EOF,
    ]


def test_caracter_inesperado():
    with pytest.raises(ScanError):
        Lexer("1 + @").run()


def test_posiciones_de_linea_y_columna():
    tokens = Lexer("a + b\nc").run()
    assert (tokens[0].line, tokens[0].column) == (1, 1)
    assert (tokens[2].line, tokens[2].column) == (1, 5)
    assert (tokens[3].line, tokens[3].column) == (2, 1)


def test_eof_final():
    assert kinds("x")[-1] is TokenKind.EOF