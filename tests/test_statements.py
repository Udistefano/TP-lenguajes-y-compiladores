import pytest

from mylox.cli import EXIT_OK, run_actions
from mylox.errors import ParseError
from mylox.nodes import ExprStmt, Literal, PrintStmt
from mylox.pipeline.lexer import Lexer
from mylox.pipeline.parser import Parser


def parse_program(source: str):
    return Parser(Lexer(source).run()).parse()


def test_programa_completo_hasta_eof():
    assert parse_program("1; 2;") == [ExprStmt(Literal(1.0)), ExprStmt(Literal(2.0))]
    assert parse_program("") == []


def test_no_ignora_sintaxis_invalida_despues_de_una_sentencia():
    with pytest.raises(ParseError):
        parse_program("1; 2 + ;")


def test_exige_punto_y_coma_tambien_al_final():
    with pytest.raises(ParseError):
        parse_program("1; 2")


def test_print_y_expresiones_sin_salida_automatica(capsys):
    assert parse_program("print true;") == [PrintStmt(Literal(True))]
    assert run_actions('2 + 2; print 2 + 2; print nil; print false; print "hola";') == EXIT_OK
    assert capsys.readouterr().out == "4\nnil\nfalse\nhola\n"
