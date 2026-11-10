"""Tests de programación orientada a objetos."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from mylox.errors import LoxRuntimeError, ParseError
from mylox.interpreter import Interpreter
from mylox.pipeline.lexer import Lexer
from mylox.pipeline.parser import Parser
from mylox.resolver import BindingResolver


def eval_expr(source: str):
    """Evalúa una expresión y devuelve su valor."""
    expression = Parser(Lexer(source + ";").run()).parse()[0].expression
    interpreter = Interpreter()
    interpreter.local_bindings.update(BindingResolver().resolve_program([expression]))
    return interpreter.evaluate(expression)


def run_program(source: str) -> str:
    """Ejecuta un programa y captura stdout."""
    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        statements = Parser(Lexer(source).run()).parse()
        interpreter = Interpreter()
        interpreter.interpret(statements)
    return buf.getvalue()


def test_clase_basica_con_metodo():
    source = """
    class Foo {
      fun bar() { return 42; }
    }
    var f = Foo();
    print f.bar();
    """
    assert run_program(source) == "42\n"


def test_this_refiere_a_la_instancia():
    source = """
    class Foo {
      fun set(x) { this.x = x; }
      fun get() { return this.x; }
    }
    var f = Foo();
    f.set(10);
    print f.get();
    """
    assert run_program(source) == "10\n"


def test_propiedades_get_y_set():
    source = """
    class Foo {}
    var f = Foo();
    f.x = 5;
    print f.x;
    f.x = f.x + 1;
    print f.x;
    """
    assert run_program(source) == "5\n6\n"


def test_herencia_simple():
    source = """
    class A {
      fun greet() { return "hello"; }
    }
    class B < A {}
    var b = B();
    print b.greet();
    """
    assert run_program(source) == "hello\n"


def test_super_llama_al_metodo_de_la_superclase():
    source = """
    class A {
      fun greet() { return "hello from A"; }
    }
    class B < A {
      fun greet() { return super.greet() + " and B"; }
    }
    var b = B();
    print b.greet();
    """
    assert run_program(source) == "hello from A and B\n"


def test_init_es_constructor():
    source = """
    class Foo {
      fun init(x) { this.x = x; }
      fun get() { return this.x; }
    }
    var f = Foo(42);
    print f.get();
    """
    assert run_program(source) == "42\n"


def test_this_fuera_de_clase_falla():
    source = "print this;"
    statements = Parser(Lexer(source).run()).parse()
    with pytest.raises(ParseError):
        BindingResolver().resolve_program(statements)


def test_super_sin_superclase_falla():
    source = "class Foo { fun bar() { return super.bar(); } }"
    statements = Parser(Lexer(source).run()).parse()
    with pytest.raises(ParseError):
        BindingResolver().resolve_program(statements)

    # El error se detecta en el resolver, no en el parser.
    source = "class Foo { fun bar() { return super.bar(); } }"
    statements = Parser(Lexer(source).run()).parse()
    with pytest.raises(ParseError):
        BindingResolver().resolve_program(statements)


def test_propiedad_indefinida_falla():
    source = """
    class Foo {}
    var f = Foo();
    print f.bar;
    """
    statements = Parser(Lexer(source).run()).parse()
    interpreter = Interpreter()
    with pytest.raises(LoxRuntimeError):
        interpreter.interpret(statements)


def test_herencia_multinivel():
    source = """
    class A {
      fun speak() { return "sound"; }
    }
    class B < A {
      fun speak() { return super.speak() + " (B)"; }
    }
    class C < B {
      fun speak() { return super.speak() + " (C)"; }
    }
    var c = C();
    print c.speak();
    """
    assert run_program(source) == "sound (B) (C)\n"
