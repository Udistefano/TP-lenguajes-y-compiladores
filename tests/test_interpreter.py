import pytest

from mylox.errors import LoxRuntimeError
from mylox.interpreter import Interpreter
from mylox.pipeline.lexer import Lexer
from mylox.pipeline.parser import Parser


def eval_expr(source: str):
    return Interpreter().evaluate(Parser(Lexer(source).run()).parse())


def test_literal_numero():
    assert eval_expr("42") == 42.0


def test_literal_string():
    assert eval_expr('"hola"') == "hola"


def test_literal_booleanos_y_nil():
    assert eval_expr("true") is True
    assert eval_expr("false") is False
    assert eval_expr("nil") is None


def test_operaciones_aritmeticas():
    assert eval_expr("2 + 3") == 5.0
    assert eval_expr("5 - 3") == 2.0
    assert eval_expr("4 * 3") == 12.0
    assert eval_expr("8 / 2") == 4.0


def test_precedencia():
    assert eval_expr("1 + 2 * 3") == 7.0
    assert eval_expr("6 / 3 - 1") == 1.0


def test_agrupacion():
    assert eval_expr("(1 + 2) * 3") == 9.0


def test_unario_negativo():
    assert eval_expr("-3") == -3.0
    assert eval_expr("--4") == 4.0
    assert eval_expr("-(3 - 1)") == -2.0


def test_not():
    assert eval_expr("!true") is False
    assert eval_expr("!false") is True
    assert eval_expr("!nil") is True


def test_concatenacion_de_cadenas():
    assert eval_expr('"a" + "b"') == "ab"


def test_comparaciones_numericas():
    assert eval_expr("3 > 2") is True
    assert eval_expr("3 >= 3") is True
    assert eval_expr("1 < 4") is True
    assert eval_expr("4 <= 2") is False


def test_igualdad():
    assert eval_expr("3 == 3") is True
    assert eval_expr("3 != 3") is False
    assert eval_expr('"a" == "a"') is True
    assert eval_expr('"a" != "b"') is True


def test_nil_y_false_no_son_iguales():
    assert eval_expr("nil == false") is False


def test_cero_es_truthy():
    assert eval_expr("!0") is False


def test_sumas_de_cadena_y_numero_fallan():
    with pytest.raises(LoxRuntimeError):
        eval_expr('"aaa" + 5')


def test_resta_de_cadenas_falla():
    with pytest.raises(LoxRuntimeError):
        eval_expr('"aaa" - "bbb"')


def test_negacion_de_cadena_falla():
    with pytest.raises(LoxRuntimeError):
        eval_expr('-"abc"')


def test_comparacion_de_cadenas_falla():
    with pytest.raises(LoxRuntimeError):
        eval_expr('"a" > "b"')


def test_error_runtime_guarda_el_token():
    with pytest.raises(LoxRuntimeError) as excinfo:
        eval_expr('"a" > "b"')
    assert excinfo.value.token.lexeme == ">"
    assert excinfo.value.token.line == 1