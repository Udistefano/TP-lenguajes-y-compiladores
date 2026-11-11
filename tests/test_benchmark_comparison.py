import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.compare import EXPECTED, Mylox, NativePython
from benchmarks.external import same_output


@pytest.mark.parametrize("bytecode", [False, True])
def test_medicion_resuelve_capturas_y_aisla_el_estado(bytecode):
    measured = Mylox(lambda name: importlib.import_module(f"mylox.{name}"), bytecode)
    source = '''
    var name = "global";
    var list = [];
    {
      fun capture() { list.push(name); }
      var name = "local";
      capture();
    }
    print list;
    '''
    for _ in range(2):
        sample, output = measured.run(source)
        assert output == '["global"]'
        assert sample["frontend_ms"] > 0
        assert sample["execution_ms"] > 0
        assert sample["total_ms"] == pytest.approx(sample["frontend_ms"] + sample["execution_ms"])


@pytest.mark.parametrize("program", ["suma", "fibonacci", "closures", "primos", "fizzbuzz"])
def test_algoritmos_de_python_coinciden_con_los_resultados_esperados(program):
    source = (ROOT / "benchmarks/native" / f"{program}.py").read_text(encoding="utf-8")
    _, output = NativePython().run(source)
    assert output == EXPECTED[program]


@pytest.mark.parametrize("actual, expected, equal", [
    ("5.00005e+09\n", "5000050000", True),
    ("4.50135e+08\n", "450135000", True),
    ("450135001\n", "450135000", False),
    ("FizzBuzz\n", "FizzBuzz", True),
    ("Fizz\n", "FizzBuzz", False),
])
def test_comparacion_externa_acepta_formato_pero_no_otro_resultado(actual, expected, equal):
    assert same_output(actual, expected) is equal
