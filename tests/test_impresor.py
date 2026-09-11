from mylox.nodes import Binary, Grouping, Literal, Unary
from mylox.printing import imprimir
from mylox.tokens import Token, TokenKind


def _token(kind: TokenKind, lexeme: str) -> Token:
    return Token(kind, lexeme)


def test_literal_verboso():
    assert imprimir(Literal(42.0)) == "Literal(42.0)"
    assert imprimir(Literal("hola")) == "Literal('hola')"
    assert imprimir(Literal(True)) == "Literal(True)"
    assert imprimir(Literal(None)) == "Literal(None)"


def test_unario():
    expr = Unary(_token(TokenKind.MINUS, "-"), Literal(1.0))
    assert imprimir(expr) == "Unary('-', Literal(1.0))"


def test_binario():
    expr = Binary(Literal(1.0), _token(TokenKind.PLUS, "+"), Literal(2.0))
    assert imprimir(expr) == "Binary(Literal(1.0), '+', Literal(2.0))"


def test_binario_anidado():
    expr = Binary(
        Literal(1.0),
        _token(TokenKind.PLUS, "+"),
        Binary(Literal(2.0), _token(TokenKind.STAR, "*"), Literal(3.0)),
    )
    assert imprimir(expr) == "Binary(Literal(1.0), '+', Binary(Literal(2.0), '*', Literal(3.0)))"


def test_grouping():
    expr = Grouping(Binary(Literal(1.0), _token(TokenKind.PLUS, "+"), Literal(2.0)))
    assert imprimir(expr) == "Grouping(Binary(Literal(1.0), '+', Literal(2.0)))"