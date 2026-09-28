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
