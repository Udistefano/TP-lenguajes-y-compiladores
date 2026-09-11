import pytest

from mylox.errors import ParseError
from mylox.nodes import Binary, Grouping, Literal, Unary
from mylox.pipeline.lexer import Lexer
from mylox.pipeline.parser import Parser


def parse(source: str):
    return Parser(Lexer(source).run()).parse()


def test_literal_numero():
    assert parse("42") == Literal(42.0)


def test_literal_string():
    assert parse('"hola"') == Literal("hola")


def test_literal_booleanos_y_nil():
    assert parse("true") == Literal(True)
    assert parse("false") == Literal(False)
    assert parse("nil") == Literal(None)


def test_multiplicacion_antes_que_suma():
    ast = parse("1 + 2 * 3")
    assert isinstance(ast, Binary)
    assert ast.operator.lexeme == "+"
    assert isinstance(ast.right, Binary)
    assert ast.right.operator.lexeme == "*"


def test_division_antes_que_resta():
    ast = parse("6 / 3 - 1")
    assert isinstance(ast, Binary)
    assert ast.operator.lexeme == "-"
    assert isinstance(ast.left, Binary)
    assert ast.left.operator.lexeme == "/"


def test_asociatividad_izquierda_a_derecha():
    ast = parse("5 - 3 - 1")
    assert isinstance(ast, Binary)
    assert ast.operator.lexeme == "-"
    assert isinstance(ast.left, Binary)
    assert ast.left.operator.lexeme == "-"
    assert ast.right == Literal(1.0)


def test_agrupacion_gana_sobre_precedencia():
    ast = parse("(1 + 2) * 3")
    assert isinstance(ast, Binary)
    assert ast.operator.lexeme == "*"
    assert isinstance(ast.left, Grouping)
    inner = ast.left.expression
    assert isinstance(inner, Binary)
    assert inner.operator.lexeme == "+"


def test_unario_negativo_y_not():
    assert parse("-1") == Unary(next(tok for tok in Lexer("-1").run() if tok.lexeme == "-"), Literal(1.0))
    assert parse("!true") == Unary(next(tok for tok in Lexer("!true").run() if tok.lexeme == "!"), Literal(True))


def test_unario_compara_comparacion():
    ast = parse("-1 + 2")
    assert isinstance(ast, Binary)
    assert isinstance(ast.left, Unary)
    assert ast.left.operator.lexeme == "-"


def test_agrupacion_anidada():
    ast = parse("((1))")
    assert ast == Grouping(Grouping(Literal(1.0)))


def test_error_expression_incompleta():
    with pytest.raises(ParseError):
        parse("1 +")


def test_error_parentesis_sin_cerrar():
    with pytest.raises(ParseError):
        parse("(2 + 2")


def test_error_sin_expresion():
    with pytest.raises(ParseError):
        parse(")")
    with pytest.raises(ParseError):
        parse("")