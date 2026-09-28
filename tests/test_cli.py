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
