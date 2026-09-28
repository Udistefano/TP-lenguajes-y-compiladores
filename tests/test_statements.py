import pytest

from mylox.cli import EXIT_OK, EXIT_RUNTIME, run_actions
from mylox.env import Env
from mylox.errors import LoxRuntimeError, ParseError
from mylox.interpreter import Interpreter
from mylox.nodes import Assign, BlockStmt, ExprStmt, IfStmt, Literal, PrintStmt, VarDecl, WhileStmt
from mylox.tokens import Token, TokenKind
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


def test_declaraciones_y_asignacion_asociativa(capsys):
    program = parse_program("var a; var b = 1; a = b = 3; print a; print b;")
    assert isinstance(program[0], VarDecl)
    assert program[0].initializer is None
    assert isinstance(program[2], ExprStmt)
    assert isinstance(program[2].expression, Assign)
    assert isinstance(program[2].expression.value, Assign)
    assert run_actions("var a; print a; var b = 1; a = b = 3; print a; print b;") == EXIT_OK
    assert capsys.readouterr().out == "nil\n3\n3\n"


def test_bloques_sombrean_y_asignan_en_ambiente_exterior(capsys):
    source = "var x = 1; var y = 0; { var x = 2; y = x; print x; { var x = 3; print x; } } print x; print y;"
    assert isinstance(parse_program(source)[2], BlockStmt)
    assert run_actions(source) == EXIT_OK
    assert capsys.readouterr().out == "2\n3\n1\n2\n"


def test_variable_local_no_escapa_y_asignacion_requiere_nombre_existente(capsys):
    assert run_actions("{ var local = 1; } print local;") == EXIT_RUNTIME
    assert "local" in capsys.readouterr().err
    assert run_actions("ausente = 2;") == EXIT_RUNTIME
    assert "ausente" in capsys.readouterr().err


def test_ambiente_se_restaura_tras_excepcion():
    interpreter = Interpreter()
    token = Token(TokenKind.IDENTIFIER, "ausente")
    with pytest.raises(LoxRuntimeError):
        interpreter.execute_block(parse_program("print ausente;"), Env(interpreter.environment))
    assert interpreter.environment is interpreter.globals
    interpreter.globals.define("ausente", 7.0)
    assert interpreter.environment.get(token) == 7.0


def test_destino_de_asignacion_invalido_y_bloque_sin_cerrar():
    with pytest.raises(ParseError):
        parse_program("(1 + 2) = 3;")
    with pytest.raises(ParseError):
        parse_program("{ print 1;")


def test_if_else_y_else_del_if_mas_cercano(capsys):
    source = 'if (false) print "error"; else print "bien"; if (true) if (false) print "error"; else print "cerca";'
    assert isinstance(parse_program(source)[0], IfStmt)
    assert run_actions(source) == EXIT_OK
    assert capsys.readouterr().out == "bien\ncerca\n"


def test_while_revalua_condicion_y_muta_variable_exterior(capsys):
    source = "var i = 0; while (i < 3) { print i; i = i + 1; } print i;"
    assert isinstance(parse_program(source)[1], WhileStmt)
    assert run_actions(source) == EXIT_OK
    assert capsys.readouterr().out == "0\n1\n2\n3\n"


def test_for_ejecuta_incremento_y_limita_ambito_del_inicializador(capsys):
    source = "var total = 0; for (var i = 1; i <= 3; i = i + 1) total = total + i; print total;"
    assert run_actions(source) == EXIT_OK
    assert capsys.readouterr().out == "6\n"
    assert run_actions("for (var i = 0; i < 1; i = i + 1) print i; print i;") == EXIT_RUNTIME
    captured = capsys.readouterr()
    assert captured.out == "0\n"
    assert "i" in captured.err


def test_for_permite_componentes_opcionales(capsys):
    source = "var i = 0; for (; i < 2;) { print i; i = i + 1; }"
    assert run_actions(source) == EXIT_OK
    assert capsys.readouterr().out == "0\n1\n"


def test_falta_parentesis_de_control_es_error_sintactico():
    with pytest.raises(ParseError):
        parse_program("if true) print 1;")
    with pytest.raises(ParseError):
        parse_program("while (true print 1;")
    with pytest.raises(ParseError):
        parse_program("for (var i = 0; i < 2; i = i + 1 print i;")
