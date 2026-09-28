"""Verifica salida, stderr y estado de los programas de aceptación de la cátedra.

Uso: python tests/strict_real_tests.py [--case 1-flow.lox] [--test-dir RUTA]
"""

from __future__ import annotations

import argparse
import difflib
import os
import subprocess
import sys
from pathlib import Path


EXPECTED_LINES = {
    "0-simple.lox": [
        "--- SIMPLE CALC ---", *(["OK"] * 10),
        "--- STRINGS ---", *(["OK"] * 2),
        "--- BOOLEAN LOGIC ---", *(["OK"] * 6),
    ],
    "1-flow.lox": [
        "--- IFs ---", "OK", "OK",
        "--- WHILEs ---", "OK",
        "--- FOR ---", "OK",
    ],
    "2-functions.lox": [
        "--- SCOPE HANDLING ---", *(["OK"] * 8),
        "--- SIMPLE FUNCTION USAGE ---", *(["OK"] * 3),
        "--- NESTED FUNCTIONS ---", *(["OK"] * 8),
        "--- VARIABLE SHADOWING ---", *(["OK"] * 3),
        "--- CLOSURE BUG ---", *(["OK"] * 2),
    ],
    "3-minsky.lox": ["--- MINSKY MACHINE ---", *(["OK"] * 6)],
    "4-fizzbuzz.lox": ["--- FIZZ BUZZ ---", *(["OK"] * 5)],
}


def main() -> int:
    """Ejecuta los casos seleccionados y devuelve 0 sólo si cumplen todo.

    --case limita la selección; sin ese argumento se comprueban los cinco
    programas. Cada archivo se ejecuta con la CLI en un proceso independiente.
    Exige stdout exacto, stderr vacío y código de salida 0. Ante una diferencia
    muestra el diagnóstico y devuelve 1 al finalizar todas las comprobaciones.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-dir", type=Path, default=Path(__file__).resolve().parents[2] / "plox" / "real-tests")
    parser.add_argument("--case", action="append", choices=EXPECTED_LINES)
    args = parser.parse_args()

    failures = 0
    for filename in args.case or EXPECTED_LINES:
        path = args.test_dir / filename
        result = subprocess.run(
            [sys.executable, "-m", "mylox.cli", str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            check=False,
        )
        expected = "\n".join(EXPECTED_LINES[filename]) + "\n"
        good = result.returncode == 0 and result.stderr == "" and result.stdout == expected
        print(f"{'OK' if good else 'FAIL'} {filename}: exit={result.returncode}")
        if good:
            continue
        failures += 1
        if result.stderr:
            print(f"stderr: {result.stderr.encode('ascii', 'backslashreplace').decode('ascii')}")
        if result.stdout != expected:
            diff = difflib.unified_diff(
                expected.splitlines(keepends=True),
                result.stdout.splitlines(keepends=True),
                fromfile="esperado",
                tofile="recibido",
            )
            print("".join(diff))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
