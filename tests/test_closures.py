"""Closures con estado compartido y vínculos léxicos estables."""

import pytest

from mylox.cli import EXIT_OK, EXIT_SCAN_PARSE, run_actions
from mylox.interpreter import Interpreter
from mylox.pipeline.lexer import Lexer
from mylox.pipeline.parser import Parser


def program(source: str):
    return Parser(Lexer(source).run()).parse()


def test_declaracion_posterior_no_cambia_lectura_del_closure(capsys):
    source = """
        var nombre = "global";
        {
            fun leer() { return nombre; }
            print leer();
            var nombre = "local";
            print leer();
        }
    """
    assert run_actions(source) == EXIT_OK
    assert capsys.readouterr().out == "global\nglobal\n"


def test_declaracion_posterior_no_cambia_destino_de_asignacion(capsys):
    source = """
        var numero = 1;
        {
            fun aumentar() { numero = numero + 1; }
            var numero = 100;
            aumentar();
            print numero;
        }
        print numero;
    """
    assert run_actions(source) == EXIT_OK
    assert capsys.readouterr().out == "100\n2\n"


def test_captura_local_exterior_con_varios_ambitos(capsys):
    source = """
        fun crear(base) {
            var cuenta = base;
            {
                fun avanzar() {
                    { cuenta = cuenta + 1; }
                    return cuenta;
                }
                var cuenta = 100;
                return avanzar;
            }
        }
        var a = crear(10);
        var b = crear(20);
        print a(); print a(); print b(); print a();
    """
    assert run_actions(source) == EXIT_OK
    assert capsys.readouterr().out == "11\n12\n21\n13\n"


def test_dos_funciones_comparten_el_mismo_estado_capturado(capsys):
    source = """
        var lector;
        fun crear() {
            var numero = 0;
            fun leer() { return numero; }
            fun aumentar() { numero = numero + 1; }
            lector = leer;
            return aumentar;
        }
        var incrementar = crear();
        incrementar(); incrementar();
        print lector();
    """
    assert run_actions(source) == EXIT_OK
    assert capsys.readouterr().out == "2\n"


def test_recursion_local_y_globales_declaradas_mas_tarde(capsys):
    source = """
        fun primero(n) { if (n == 0) return mensaje; return segundo(n - 1); }
        fun segundo(n) { return primero(n); }
        var mensaje = "listo";
        print primero(2);
        {
            fun sumar(n) { if (n == 0) return 0; return n + sumar(n - 1); }
            print sumar(3);
        }
    """
    assert run_actions(source) == EXIT_OK
    assert capsys.readouterr().out == "listo\n6\n"


def test_closure_sigue_funcionando_al_interpretar_otro_programa(capsys):
    interpreter = Interpreter()
    interpreter.interpret(program("""
        fun crear() {
            var n = 0;
            fun siguiente() { n = n + 1; return n; }
            return siguiente;
        }
        var contador = crear();
    """))
    interpreter.interpret(program("print contador();"))
    interpreter.interpret(program("{ var n = 99; print contador(); }"))
    assert capsys.readouterr().out == "1\n2\n"
    assert interpreter.environment is interpreter.globals


@pytest.mark.parametrize("source", [
    "return;", "print 1; { return 2; }", "if (false) return;",
    "fun valida() { return; } return;",
])
def test_return_fuera_de_funcion_se_detecta_antes_de_ejecutar(source, capsys):
    assert run_actions(source) == EXIT_SCAN_PARSE
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "return fuera de una función" in captured.err


def test_inicializadores_y_redeclaraciones_conservan_el_orden(capsys):
    source = "var n = 1; { var n = n + 1; var n = n + 1; print n; } print n;"
    assert run_actions(source) == EXIT_OK
    assert capsys.readouterr().out == "3\n1\n"
