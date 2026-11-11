from pathlib import Path

import pytest
from mylox.bytecode.compiler import Compiler
from mylox.bytecode.disassembler import disassemble
from mylox.bytecode.opcodes import OpCode, stack_effect
from mylox.bytecode.vm import VM
from mylox.cli import run_actions, run_tree
from mylox.pipeline.lexer import Lexer


@pytest.fixture(params=["tree-walk"])
def backend(request):
    return request.param


@pytest.mark.parametrize("source, expected", [
    ('print []; print [1, "hola", true, nil, [2]];', '[]\n[1, "hola", true, nil, [2]]\n'),
    ('print [10, 20][0]; print ([10, 20])[1];', '10\n20\n'),
    ('var a = [[1, 2]]; a[0][1] = 7; print a;', '[[1, 7]]\n'),
    ('var a = [1]; print a[0] = 8; print a[0];', '8\n8\n'),
    ('var a = [1]; var b = a; b[0] = 9; print a; print a == b;', '[9]\ntrue\n'),
    ('print [] == []; print [1] == [1]; print [] == nil;', 'false\nfalse\nfalse\n'),
    ('print ![]; print [] or "no"; print [] and "si";', 'false\n[]\nsi\n'),
    ('var a = []; print a.push(5); a.push(7); print a.length; print a.pop(); print a;', 'nil\n2\n7\n[5]\n'),
    ('var a = []; var push = a.push; push(8); var pop = a.pop; print pop(); print a.length;', '8\n0\n'),
    ('var a = []; a.push(a); print a; print a[0] == a;', '[[...]]\ntrue\n'),
    ('var a = []; var b = [a]; a.push(b); print a;', '[[[...]]]\n'),
    ('var a = [1]; print [a, a]; print a;', '[[1], [1]]\n[1]\n'),
    ('fun make() { return []; } var a = make(); a.push(1); print make();', '[]\n'),
    ('fun make() { var a = [1]; fun f() { a[0] = a[0] + 1; return a[0]; } return f; } var f = make(); print f(); print f();', '2\n3\n'),
    ('fun f() { return 42; } print [f][0]();', '42\n'),
    ('class Box { init() { this.items = [2]; } } var boxes = [Box()]; boxes[0].items[0] = 6; print boxes[0].items;', '[6]\n'),
    ('var a = [0]; fun get() { return a; } get()[0] = 4; print a;', '[4]\n'),
    ('var a = [0]; var b = [0]; a[0] = b[0] = 3; print a; print b;', '[3]\n[3]\n'),
    ('var a = []; for (var i = 0; i < 300; i = i + 1) a.push(i); print a.length; print a[299];', '300\n299\n'),
    ('var n = 0; fun next() { n = n + 1; return n; } print [next(), next(), next()];', '[1, 2, 3]\n'),
    ('''var a = [0];
        fun object() { print "obj"; return a; }
        fun index() { print "index"; return 0; }
        fun value() { print "value"; return 9; }
        object()[index()] = value(); print a;''', 'obj\nindex\nvalue\n[9]\n'),
])
def test_listas(backend, capsys, source, expected):
    assert run_actions(source, backend) == 0
    output = capsys.readouterr()
    assert output.out == expected
    assert output.err == ""


@pytest.mark.parametrize("source, message", [
    ('print [1][-1];', 'out of bounds'),
    ('print [1][1];', 'out of bounds'),
    ('print [1][0.5];', 'integer'),
    ('print [1][true];', 'integer'),
    ('print [1]["0"];', 'integer'),
    ('print [1][nil];', 'integer'),
    ('print [1][[]];', 'integer'),
    ('print [][0];', 'out of bounds'),
    ('var a = [1]; a[1] = 2;', 'out of bounds'),
    ('var a = [1]; a[-1] = 2;', 'out of bounds'),
    ('var a = [1]; a[false] = 2;', 'integer'),
    ('print "abc"[0];', 'Only lists'),
    ('var a = 1; a[0] = 2;', 'Only lists'),
    ('[].pop();', 'empty list'),
    ('[].push();', 'Expected 1 arguments'),
    ('[].pop(1);', 'Expected 0 arguments'),
    ('var a = []; a.length = 4;', 'read-only'),
    ('var a = []; a.push = 4;', 'read-only'),
    ('print [].missing;', 'Undefined list property'),
])
def test_errores_de_listas(backend, capsys, source, message):
    assert run_actions("\n" + source, backend) == 70
    output = capsys.readouterr()
    assert output.out == ""
    assert message in output.err
    assert "línea 2" in output.err
    assert "Traceback" not in output.err


@pytest.mark.parametrize("source", [
    'print [1,];', 'print [1 2];', 'print [1;', 'print [1][];',
    'var a = [1]; 1 + a[0] = 2;',
    'var a = [1]; !a[0] = 2;',
    'var a = [1]; true or a[0] = 2;',
    'var a = [1]; (a[0]) = 2;',
])
def test_sintaxis_invalida(backend, capsys, source):
    assert run_actions(source, backend) == 65
    assert "Traceback" not in capsys.readouterr().err


def test_limite_de_literal(backend, capsys):
    source = "[" + ",".join(["0"] * 255) + "]"
    assert run_actions(f"print {source}.length;", backend) == 0
    assert capsys.readouterr().out == "255\n"
    source = "[" + ",".join(["0"] * 256) + "]"
    assert run_actions(f"print {source};", backend) == 65
    assert "255 elementos" in capsys.readouterr().err


def test_ast_de_lectura_y_escritura(capsys):
    assert run_tree("var a = [1]; a[0] = a[0] + 1;") == 0
    tree = capsys.readouterr().out
    assert "List([Literal(1.0)])" in tree
    assert "IndexSet(" in tree
    assert "Index(" in tree






