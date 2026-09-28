from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

from mylox.errors import LoxError
from mylox.interpreter import Interpreter
from mylox.pipeline.lexer import Lexer
from mylox.pipeline.parser import Parser

EXIT_OK = 0
EXIT_ERROR = 65


def ejecutar(source: str) -> None:
    """Escanea, parsea y evalúa un programa completo sin imprimir su resultado."""

    tree = Parser(Lexer(source).run()).parse()
    Interpreter().interpret(tree)


def medir(source: str, repeticiones: int) -> list[float]:
    """Ejecuta ``ejecutar`` ``repeticiones`` veces y devuelve los tiempos en segundos."""

    tiempos: list[float] = []

    for _ in range(repeticiones):
        inicio = time.perf_counter()
        ejecutar(source)
        tiempos.append(time.perf_counter() - inicio)

    return tiempos


def percentil(ordenados: list[float], p: float) -> float:
    """Percentil ``p`` (rango cercano) sobre una lista ya ordenada de tiempos."""

    indice = min(len(ordenados) - 1, int(-(-p * len(ordenados) // 1)) - 1)
    return ordenados[indice]


def ms(segundos: float) -> float:
    return segundos * 1000


def informar(archivo: Path, tiempos: list[float]) -> None:
    """Imprime la tabla de resultados del benchmark."""

    ordenados = sorted(tiempos)
    promedio = statistics.mean(ordenados)
    minimo = ordenados[0]
    maximo = ordenados[-1]
    mediana = percentil(ordenados, 0.50)
    p95 = percentil(ordenados, 0.95)

    print(f"archivo: {archivo}")
    print(f"muestras: {len(tiempos)}")
    print()
    print(f"{'mylox':<8} {'prom':>10} {'min':>10} {'max':>10} {'p50':>10} {'p95':>10}")
    print(f"{'mylox':<8} {ms(promedio):>10.2f} {ms(minimo):>10.2f} {ms(maximo):>10.2f} {ms(mediana):>10.2f} {ms(p95):>10.2f}")


def main(argv: list[str] | None = None) -> int:
    """Corre un archivo .lox varias veces y reporta estadísticas de tiempo."""

    parser = argparse.ArgumentParser(
        prog="bench",
        description="Benchmarks de rendimiento de mylox contra un archivo .lox",
    )
    parser.add_argument("file", type=Path, help="archivo .lox a ejecutar")
    parser.add_argument(
        "-n",
        "--repeticiones",
        type=int,
        default=20,
        help="cantidad de ejecuciones medidas (por defecto: 20)",
    )

    args = parser.parse_args(argv)

    try:
        source = args.file.read_text(encoding="utf-8")
    except OSError as error:
        print(f"[error] no se pudo leer el archivo: {error}", file=sys.stderr)
        return EXIT_ERROR

    try:
        tiempos = medir(source, args.repeticiones)
    except LoxError as error:
        print(f"[error] {error}", file=sys.stderr)
        return EXIT_ERROR

    informar(args.file, tiempos)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
