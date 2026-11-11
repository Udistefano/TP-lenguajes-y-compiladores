import io
import sys

import pytest

from mylox.cli import (
    EXIT_OK,
    EXIT_RUNTIME,
    EXIT_SCAN_PARSE,
    main,
    report_error,
    run_actions,
    run_tokens,
    run_tree,
)
from mylox.errors import LoxRuntimeError
from mylox.tokens import Token, TokenKind


def test_run_tokens_imprime_tokens(capsys):
    assert run_tokens("1 + 2") == EXIT_OK
    out = capsys.readouterr().out
    assert "NUMBER<1.0>" in out
    assert "PLUS" in out
    assert "EOF" in out


def test_run_tokens_error_de_escaneo(capsys):
    assert run_tokens("1 + @") == EXIT_SCAN_PARSE
    assert "Carácter inesperado" in capsys.readouterr().err


def test_run_tree_imprime_ast(capsys):
    assert run_tree("1 + 2;") == EXIT_OK
    assert "Binary(Literal(1.0), '+', Literal(2.0))" in capsys.readouterr().out


def test_run_tree_error_de_parseo(capsys):
    assert run_tree("1 +;") == EXIT_SCAN_PARSE
    assert "Se esperaba una expresión" in capsys.readouterr().err


def test_run_actions_evalua(capsys):
    assert run_actions("2 + 2; print 2 + 2;") == EXIT_OK
    assert capsys.readouterr().out == "4\n"


def test_run_actions_error_runtime(capsys):
    assert run_actions('"a" > "b";') == EXIT_RUNTIME
    err = capsys.readouterr().err
    assert "must be numbers" in err
    assert "línea 1" in err


def test_report_error_scan_y_parse_devuelven_65(capsys):
    from mylox.errors import ParseError, ScanError

    assert report_error(ScanError("algo")) == EXIT_SCAN_PARSE
    assert report_error(ParseError("algo")) == EXIT_SCAN_PARSE
    err = capsys.readouterr().err
    assert "algo" in err


def test_report_error_runtime_devuelve_70_y_posicion(capsys):
    token = Token(TokenKind.GREATER, ">", None, 1, 5)
    error = LoxRuntimeError(token, "Operands of > must be numbers")
    assert report_error(error) == EXIT_RUNTIME
    err = capsys.readouterr().err
    assert "línea 1, columna 5" in err


def test_division_por_cero_no_rompe_la_cli(capsys, tmp_path):
    source = tmp_path / "cero.lox"
    source.write_text("1 / 0;", encoding="utf-8")
    assert main([str(source)]) == EXIT_RUNTIME
    err = capsys.readouterr().err
    assert "Division by zero" in err
    assert "Traceback" not in err


def test_repl_continua_tras_division_por_cero(capsys, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("1 / 0;\nprint 2 + 2;\n"))
    assert main([]) == EXIT_OK
    captured = capsys.readouterr()
    assert "Division by zero" in captured.err
    # El prompt "> " se escribe en stdout, junto a la salida del print.
    assert "4" in captured.out
    assert "Traceback" not in captured.err


def test_recursion_infinita_no_muestra_traza(capsys, tmp_path):
    source = tmp_path / "infinita.lox"
    source.write_text("fun f(n) { return f(n + 1); } f(0);", encoding="utf-8")
    assert main([str(source)]) == EXIT_RUNTIME
    err = capsys.readouterr().err
    assert "recursión excedida" in err
    assert "Traceback" not in err


def test_main_con_archivo_run(capsys, tmp_path):
    source = tmp_path / "calc.lox"
    source.write_text("1 + 2 * 3; print 1 + 2 * 3;", encoding="utf-8")
    assert main([str(source)]) == EXIT_OK
    assert capsys.readouterr().out == "7\n"


def test_main_con_archivo_tokens(capsys, tmp_path):
    source = tmp_path / "calc.lox"
    source.write_text("1 + 2", encoding="utf-8")
    assert main(["--tokens", str(source)]) == EXIT_OK
    assert "NUMBER<1.0>" in capsys.readouterr().out


def test_main_archivo_inexistente(capsys):
    assert main(["/no/existe.lox"]) == 1
    assert "no se pudo leer el archivo" in capsys.readouterr().err


def test_main_sin_archivo_usa_repl(capsys, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("print 2 + 2;\n"))
    assert main([]) == EXIT_OK
    assert "4\n" in capsys.readouterr().out


def test_main_version(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["-v"])
    assert excinfo.value.code == 0
    assert "mylox" in capsys.readouterr().out


@pytest.mark.parametrize("backend", ['tree-walk', 'bytecode'])
def test_repl_conserva_variables_funciones_clases_y_listas(backend, capsys, monkeypatch):
    source = '''var n = 1; var a = [];
fun f() { n = n + 1; return n; }
class Box { init(value) { this.value = value; } }
a.push(Box(f()));
print a[0].value; print n;
'''
    monkeypatch.setattr(sys, 'stdin', io.StringIO(source))
    assert main(['--backend', backend]) == EXIT_OK
    output = capsys.readouterr()
    assert output.out.replace('> ', '').strip() == '2\n2'
    assert output.err == ''


@pytest.mark.parametrize("backend", ['tree-walk', 'bytecode'])
def test_repl_recupera_capturas_despues_de_un_error(backend, capsys, monkeypatch):
    source = '''var saved; fun fail() { var n = 1; fun get() { return n; } saved = get; n = 2; 1 / 0; } fail();
print saved();
var broken = ;
print saved();
'''
    monkeypatch.setattr(sys, 'stdin', io.StringIO(source))
    assert main(['--backend', backend]) == EXIT_OK
    output = capsys.readouterr()
    assert output.out.replace('> ', '').strip() == '2\n2'
    assert 'Division by zero' in output.err
    assert 'Traceback' not in output.err


@pytest.mark.parametrize("backend", ['tree-walk', 'bytecode'])
@pytest.mark.parametrize("source", ['print ²;', 'print 1²;', 'print ٣;'])
def test_digitos_fuera_de_ascii_son_error_de_escaneo(backend, source, capsys):
    assert run_actions(source, backend) == EXIT_SCAN_PARSE
    assert 'Carácter inesperado' in capsys.readouterr().err


def test_arbol_profundo_no_muestra_traceback(capsys):
    assert run_tree('print ' + ' + '.join(['1'] * 1500) + ';') == EXIT_RUNTIME
    output = capsys.readouterr()
    assert output.out == ''
    assert 'recursión excedida' in output.err


def test_archivo_no_utf8_informa_error(capsys, tmp_path):
    path = tmp_path / 'invalid.lox'
    path.write_bytes(b'\xff')
    assert main([str(path)]) == 1
    assert 'no se pudo leer el archivo' in capsys.readouterr().err


@pytest.mark.parametrize("statement, padding", [("if", 32764), ("while", 32762)])
@pytest.mark.parametrize("negations, expected", [("!", EXIT_OK), ("!!", EXIT_SCAN_PARSE)])
def test_limite_de_saltos(statement, padding, negations, expected, capsys):
    body = "nil;" * padding + negations + "nil;"
    source = f"{statement} (false) {{ {body} }} print 2;"
    assert run_actions(source, "bytecode") == expected
    output = capsys.readouterr()
    if expected == EXIT_OK:
        assert output.out == "2\n"
        assert output.err == ""
    else:
        assert output.out == ""
        assert "65535" in output.err
        assert "línea 1" in output.err


