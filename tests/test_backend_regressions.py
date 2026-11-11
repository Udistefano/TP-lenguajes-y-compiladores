import pytest

from mylox.cli import run_actions


@pytest.fixture(params=["tree-walk", "bytecode"])
def backend(request):
    return request.param


@pytest.mark.parametrize("source, expected", [
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












