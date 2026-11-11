import pytest

from mylox.cli import run_actions


@pytest.fixture(params=["tree-walk", "bytecode"])
def backend(request):
    return request.param


@pytest.mark.parametrize("source, expected", [
    ('''var get; fun noop() {}
        fun f() { var x = 1; { fun capture() { return x; } get = capture; }
                  noop(); x = 2; }
        f(); print get();''', '2\n'),
    ('''var first; var second;
        fun f() {
          var x = "outer";
          fun a() { return x; }
          first = a;
          { var y = "inner"; fun b() { return y; } second = b; }
          var overwrite = "wrong";
          print second();
        }
        f(); print first(); print second();''', 'inner\nouter\ninner\n'),
    ('''class A { m() { return "A"; } }
        class B < A { get() { fun f() { return super.m(); } return f; } }
        var f = B().get(); print f();''', 'A\n'),
    ('''class A { m() { return "A"; } }
        class B < A { m() { return super.m() + "B"; } }
        class C < B {} var c = C(); B = C; print c.m();''', 'AB\n'),
    ('''fun make() { class A { m() { return "A"; } }
                    class B < A { m() { return super.m() + "B"; } }
                    class C < B {} return C(); }
        print make().m();''', 'AB\n'),
    ('{ class A { make() { return A(); } } print A().make(); }', 'A instance\n'),
    ('''fun make(x) { class A { m() { return x; } }
                    class B < A { m() { return super.m() + x; } } return B; }
        var B = make("X"); print B().m();''', 'XX\n'),
    ('class A {} var a = A(); fun get() { return a; } get().x = 42; print a.x;', '42\n'),
    ('class A {} var a = A(); (a).x = 42; print (a).x;', '42\n'),
    ('class A {} var a = A(); a.child = A(); a.child.x = 42; print a.child.x;', '42\n'),
    ('fun f() { return 7; } print (f)();', '7\n'),
    ('class A {} var a = A(); print A() == A(); print a == a;', 'false\ntrue\n'),
    ('class A {} var a = A(); var b = A(); a.self = a; b.self = b; print a == b;', 'false\n'),
    ('fun make() { class A {} return A; } print make() == make();', 'false\n'),
    ('fun make() { fun f() {} return f; } print make() == make();', 'false\n'),
])
def test_regresiones(backend, capsys, source, expected):
    assert run_actions(source, backend) == 0
    output = capsys.readouterr()
    assert output.out == expected
    assert output.err == ""


@pytest.mark.parametrize("source", [
    'class A {} class A < A {}',
    'class A { m() { super.m(); } }',
    'super.m();',
])
def test_errores_de_herencia_antes_de_ejecutar(backend, capsys, source):
    assert run_actions(source, backend) == 65
    output = capsys.readouterr()
    assert output.out == ""
    assert "Traceback" not in output.err










