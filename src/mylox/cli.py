from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .errors import LoxRuntimeError, ParseError, ScanError
from .interpreter import Interpreter
from .pipeline.lexer import Lexer
from .pipeline.parser import Parser
from .printing import imprimir

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_SCAN_PARSE = 65
EXIT_RUNTIME = 70


def run_tokens(source: str) -> int:
    """Modo ``--tokens``: escanea la fuente e imprime cada token por línea."""
    try:
        tokens = Lexer(source).run()
    except ScanError as error:
        return report_error(error)

    # Cada token se imprime con su representación textual (kind y literal).
    for token in tokens:
        print(token)
    return EXIT_OK


def run_tree(source: str) -> int:
    """Modo ``--tree``: escanea y parsea la fuente, e imprime el AST."""
    try:
        tree = Parser(Lexer(source).run()).parse()
    except (ScanError, ParseError) as error:
        return report_error(error)

    # imprimir() es nuestro visitor Impresor: representación verbosa del árbol.
    print(imprimir(tree))
    return EXIT_OK


def run_actions(source: str) -> int:
    """Modo ejecución (default): escanea, parsea y evalúa la fuente."""
    try:
        tree = Parser(Lexer(source).run()).parse()
        value = Interpreter().evaluate(tree)
    except (ScanError, ParseError) as error:
        return report_error(error)
    except LoxRuntimeError as error:
        return report_error(error)

    print(value)
    return EXIT_OK


def report_error(error: Exception) -> int:
    """Imprime el error recibido en stderr y devuelve el código de salida."""
    if isinstance(error, (ScanError, ParseError)):
        print(f"[error] {error}", file=sys.stderr)
        return EXIT_SCAN_PARSE

    if isinstance(error, LoxRuntimeError):
        # El token del error guarda la posición donde falló la ejecución.
        token = error.token
        print(
            f"[error] {error} (línea {token.line}, columna {token.column})",
            file=sys.stderr,
        )
        return EXIT_RUNTIME

    print(f"[error] {error}", file=sys.stderr)
    return EXIT_USAGE


def repl() -> int:
    """Bucle interactivo que lee líneas de la entrada estándar y las ejecuta."""
    # Sin archivo, la CLI entra en modo REPL hasta que el usuario salga (EOF/^C).
    while True:
        try:
            source = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return EXIT_OK

        # Las líneas en blanco se ignoran sin intentar ejecutarlas.
        if not source.strip():
            continue

        # En el REPL corremos en modo ejecución y continuamos tras cada error.
        run_actions(source)


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada de la CLI; orquesta los argumentos y el modo elegido."""
    parser = argparse.ArgumentParser(
        prog="mylox",
        description="Intérprete de Lox (TPLenguajes y Compiladores I, FIUBA)",
    )

    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--tokens",
        action="store_true",
        help="modo escaneo: imprime la lista de tokens",
    )
    modes.add_argument(
        "--tree",
        action="store_true",
        help="modo parseo: imprime el árbol de sintaxis abstracta",
    )

    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        help="archivo a interpretar; si no se pasa, se abre un REPL",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"mylox {__version__}",
    )

    args = parser.parse_args(argv)

    if args.file is not None:
        try:
            source = args.file.read_text(encoding="utf-8")
        except OSError as error:
            print(f"[error] no se pudo leer el archivo: {error}", file=sys.stderr)
            return EXIT_USAGE
    else:
        return repl()

    if args.tokens:
        return run_tokens(source)
    if args.tree:
        return run_tree(source)
    return run_actions(source)


if __name__ == "__main__":
    sys.exit(main())