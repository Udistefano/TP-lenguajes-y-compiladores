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
    ('var a = 1; { var a = a + 1; print a; } print a;', '2\n1\n'),
    ('{ var a = 1; fun get() { return a; } var a = 2; print get(); }', '2\n'),
    ('{ fun f() { return f; } var old = f; fun f() { return 7; } print old()(); }', '7\n'),
    ('{ class A {} fun get() { return A; } class A { m() { return 3; } } print get()().m(); }', '3\n'),
    ('{ var f = 1; fun f() { return 2; } print f(); var f = f() + 1; print f; }', '2\n3\n'),
    ('fun f(a, a) { fun get() { return a; } var a = a + 1; return get; } print f(1, 2)();', '3\n'),
    ('class A { m(a, a) { return a; } } print A().m(1, 2);', '2\n'),
    ('fun f() {} print f; print [f];', '<fn f>\n[<fn f>]\n'),
    ('class A { m() {} } var a = A(); print a.m; print [a.m];', '<fn m>\n[<fn m>]\n'),
    ('''class Base { m() { return "A"; } }
        { var X = "antes"; fun get() { return X; }
          class X < Base {
            m() { return super.m() + "B"; }
            make() { return X(); }
          }
          var Sub = get(); print Sub().m(); print Sub().make().m(); }''', 'AB\nAB\n'),
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


def test_expresion_profunda_sin_traceback(backend, capsys):
    source = "print " + "(" * 300 + "1" + ")" * 300 + ";"
    assert run_actions(source, backend) == 70
    output = capsys.readouterr()
    assert "recursión excedida" in output.err
    assert "Traceback" not in output.err


def test_recursion_sin_limite_es_un_error_de_lox(backend, capsys):
    assert run_actions("fun f() { f(); } f();", backend) == 70
    output = capsys.readouterr()
    assert output.out == ""
    assert "[error]" in output.err
    assert "Traceback" not in output.err


def test_inicializador_sin_nombre_anterior_falla_en_runtime(backend, capsys):
    assert run_actions('{ var a = a; }', backend) == 70
    assert "Traceback" not in capsys.readouterr().err


def test_comparaciones_con_nan_e_infinito(backend, capsys):
    source = 'var inf = ' + '9' * 310 + ''';
        var n = inf - inf;
        print n < 0; print n > 0; print n <= 0; print n >= 0;
        print 0 <= n; print 0 >= n; print n == n; print n != n;
        print inf >= inf; print inf <= inf; print inf > 0; print -inf < 0;
        print 2 >= 2; print 2 <= 2; print 2 >= 3; print 3 <= 2;
    '''
    assert run_actions(source, backend) == 0
    output = capsys.readouterr()
    assert output.out.splitlines() == ['false'] * 7 + ['true'] * 7 + ['false'] * 2
    assert output.err == ''


@pytest.mark.parametrize("operator", ['<=', '>='])
def test_comparaciones_exigen_numeros(backend, capsys, operator):
    assert run_actions(f'print "x" {operator} 1;', backend) == 70
    assert 'must be numbers' in capsys.readouterr().err
