"""Pruebas pequeñas de funciones junto con statements, ámbitos y flujo."""

import pytest

from mylox.cli import EXIT_OK, EXIT_RUNTIME, run_actions, run_tree
from mylox.errors import LoxRuntimeError, ParseError
from mylox.interpreter import Interpreter
from mylox.nodes import Binary, Call, FunctionDecl, ReturnStmt, Variable
from mylox.pipeline.lexer import Lexer
from mylox.pipeline.parser import Parser
from mylox.tokens import Token, TokenKind


def program(source: str):
    return Parser(Lexer(source).run()).parse()


def test_declaracion_retorno_y_llamada_en_ast():
    declaration, output = program("fun suma(a, b) { return a + b; } print suma(2, 3);")
    assert isinstance(declaration, FunctionDecl)
    assert declaration.name.lexeme == "suma"
    assert [parameter.lexeme for parameter in declaration.parameters] == ["a", "b"]
    assert isinstance(declaration.body[0], ReturnStmt)
    assert isinstance(declaration.body[0].value, Binary)
    assert isinstance(output.expression, Call)
    assert isinstance(output.expression.callee, Variable)


@pytest.mark.parametrize("source", [
    "fun () {}", "fun f(a,) {}", "fun f(1) {}", "fun f() print 1;",
    "fun f() { return 1 }", "fun f() {",
])
def test_funcion_mal_formada_es_error_de_parseo(source):
    with pytest.raises(ParseError):
        program(source)


@pytest.mark.parametrize(("body", "expected"), [
    ("", "nil\n"), ("return;", "nil\n"), ("return 0;", "0\n"),
    ('return "hola";', "hola\n"),
])
def test_retorno_explicito_o_implicito(body, expected, capsys):
    assert run_actions(f"fun valor() {{ {body} }} print valor();") == EXIT_OK
    assert capsys.readouterr().out == expected


def test_parametros_no_modifican_el_ambito_del_llamador(capsys):
    source = "var a = 10; fun suma(a, b) { a = a + b; return a; } print suma(2, 3); print a;"
    assert run_actions(source) == EXIT_OK
    assert capsys.readouterr().out == "5\n10\n"


def test_recursion_y_funciones_como_argumentos(capsys):
    source = """
        fun factorial(n) {
            if (n <= 1) return 1;
            return n * factorial(n - 1);
        }
        fun aplicar(funcion, valor) { return funcion(valor); }
        print aplicar(factorial, 5);
    """
    assert run_actions(source) == EXIT_OK
    assert capsys.readouterr().out == "120\n"


def test_return_sale_de_bloques_y_bucles_y_restaura_el_ambito(capsys):
    source = """
        var resultado = 9;
        fun buscar() {
            for (var i = 0; i < 3; i = i + 1) {
                while (true) { if (i == 1) return i; return 0; }
            }
            print "inalcanzable";
        }
        print buscar();
        print resultado;
    """
    interpreter = Interpreter()
    interpreter.interpret(program(source))
    assert interpreter.environment is interpreter.globals
    assert capsys.readouterr().out == "0\n9\n"


@pytest.mark.parametrize("source", [
    "fun f(a) {} f();", "fun f() {} f(1);", "var numero = 1; numero();",
])
def test_aridad_y_valores_no_invocables_producen_error_runtime(source, capsys):
    assert run_actions(source) == EXIT_RUNTIME
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("[error]")


def test_argumentos_en_orden_incluso_antes_de_error_de_invocacion(capsys):
    interpreter = Interpreter()
    source = """
        var contador = 0;
        fun siguiente() { contador = contador + 1; return contador; }
        fun mostrar(a, b) { print a; print b; }
        mostrar(siguiente(), siguiente());
        1(siguiente());
    """
    with pytest.raises(LoxRuntimeError, match="Can only call"):
        interpreter.interpret(program(source))
    assert capsys.readouterr().out == "1\n2\n"
    assert interpreter.globals.get(Token(TokenKind.IDENTIFIER, "contador")) == 3.0


def test_error_en_funcion_restaura_ambito_del_llamador():
    interpreter = Interpreter()
    with pytest.raises(LoxRuntimeError):
        interpreter.interpret(program("fun falla() { { print ausente; } } falla();"))
    assert interpreter.environment is interpreter.globals


def test_tree_muestra_funcion_y_return(capsys):
    assert run_tree("fun f(a) { return a; } fun vacia() { return; }") == EXIT_OK
    output = capsys.readouterr().out
    assert "FunctionDecl('f', ['a'], [ReturnStmt(Variable('a'))])" in output
    assert "FunctionDecl('vacia', [], [ReturnStmt(nil)])" in output
