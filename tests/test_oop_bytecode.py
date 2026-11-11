"""Pruebas de OOP en el backend de bytecode y paridad con tree-walk."""
from __future__ import annotations

import io
import contextlib
import os
import tempfile

import pytest

from mylox.cli import main


def run(source: str, backend: str) -> tuple[str, str, int]:
    """Ejecuta un programa con el backend indicado y devuelve (stdout, stderr, código)."""
    fd, path = tempfile.mkstemp(suffix=".lox")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(source)
        buf = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
            code = main([path, "--backend", backend])
        return buf.getvalue(), err.getvalue(), code
    finally:
        os.unlink(path)


OOP_PROGRAMS = [
    # clase básica con método
    """
    class Foo { bar() { return 42; } }
    var f = Foo();
    print f.bar();
    """,
    # this refiere a la instancia
    """
    class Foo {
      set(x) { this.x = x; }
      get() { return this.x; }
    }
    var f = Foo();
    f.set(10);
    print f.get();
    """,
    # herencia simple
    """
    class A { saludar() { return "hola de A"; } }
    class B < A { }
    var b = B();
    print b.saludar();
    """,
    # super en constructor y método
    """
    class Persona {
      init(nombre) { this.nombre = nombre; }
      decir() { return "Soy " + this.nombre; }
    }
    class Estudiante < Persona {
      init(nombre, carrera) {
        super.init(nombre);
        this.carrera = carrera;
      }
      decir() { return super.decir() + ", estudio " + this.carrera; }
    }
    var e = Estudiante("Ana", "Fisica");
    print e.decir();
    print e.nombre;
    print e.carrera;
    """,
    # herencia de dos niveles con super
    """
    class A { m() { return "A"; } }
    class B < A { m() { return super.m() + "B"; } }
    class C < B { m() { return super.m() + "C"; } }
    var c = C();
    print c.m();
    """,
    # campos asignados desde afuera y encadenamiento
    """
    class Builder {
      init() { this.parts = ""; }
      add(s) { this.parts = this.parts + s; return this; }
      build() { return this.parts; }
    }
    print Builder().add("a").add("b").add("c").build();
    """,
    # closure dentro de método que captura this
    """
    class Foo {
      init(x) { this.x = x; }
      bar() {
        fun f() { return this.x; }
        return f();
      }
    }
    var o = Foo(42);
    print o.bar();
    """,
    # contador con while
    """
    class Contador {
      init() { this.n = 0; }
      inc() { this.n = this.n + 1; }
      valor() { return this.n; }
    }
    var c = Contador();
    var i = 0;
    while (i < 5) { c.inc(); i = i + 1; }
    print c.valor();
    """,
    # instancia dentro de función
    """
    class Punto { init(x, y) { this.x = x; this.y = y; }
      suma() { return this.x + this.y; } }
    fun crear(a, b) { var pt = Punto(a, b); return pt; }
    print crear(3, 4).suma();
    """,
    # print de clase e instancia
    """
    class Foo { }
    var f = Foo();
    print Foo;
    print f;
    """,
    # método pasado como valor (bound method)
    """
    class Foo { get() { return 7; } }
    var f = Foo();
    var m = f.get;
    print m();
    """,
]


@pytest.mark.parametrize("source", OOP_PROGRAMS)
def test_oop_bytecode_runs(source):
    out, err, code = run(source, "bytecode")
    assert code == 0, f"stderr: {err}"
    assert err == ""


@pytest.mark.parametrize("source", OOP_PROGRAMS)
def test_oop_parity(source):
    """La salida del backend bytecode debe coincidir con la de tree-walk."""
    out_tw, err_tw, code_tw = run(source, "tree-walk")
    out_bc, err_bc, code_bc = run(source, "bytecode")
    assert code_tw == code_bc, f"exit codes differ: tree={code_tw} bc={code_bc}\n{err_tw}\n{err_bc}"
    assert out_tw == out_bc, f"stdout differs:\ntree:\n{out_tw}\nbc:\n{out_bc}"
    assert err_tw == err_bc, f"stderr differs:\ntree:\n{err_tw}\nbc:\n{err_bc}"


# Casos de error de OOP en bytecode
def test_error_propiedad_indefinida_bytecode():
    source = """
    class Foo { }
    var f = Foo();
    print f.bar;
    """
    out, err, code = run(source, "bytecode")
    assert code != 0
    assert "Undefined property 'bar'" in err


def test_error_super_sin_superclase_bytecode():
    source = """
    class Foo { m() { return super.m(); } }
    var f = Foo();
    print f.m();
    """
    out, err, code = run(source, "bytecode")
    assert code != 0
    assert code == 65
    assert "sin superclase" in err


def test_error_llamar_no_callable_bytecode():
    source = """
    class Foo { x() { return 1; } }
    var f = Foo();
    var m = f.x;
    print m + 1;
    """
    out, err, code = run(source, "bytecode")
    assert code != 0
