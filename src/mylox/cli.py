from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .bytecode.compiler import Compiler
from .bytecode.disassembler import disassemble, raw_bytes
from .bytecode.vm import VM
from .errors import (
    CompileError,
    LoxRuntimeError,
    ParseError,
    ScanError,
    VMRuntimeError,
)
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

    for token in tokens:
        print(token)
    return EXIT_OK


def run_tree(source: str) -> int:
    """Modo ``--tree``: escanea y parsea la fuente, e imprime el AST."""
    try:
        tree = Parser(Lexer(source).run()).parse()
    except (ScanError, ParseError) as error:
        return report_error(error)

    print(imprimir(tree))
    return EXIT_OK


def run_actions(
    source: str, backend: str = "tree-walk", debug: bool = False
) -> int:
    """Modo ejecución (default): escanea, parsea y evalúa la fuente."""
    if backend == "bytecode":
        try:
            tokens = Lexer(source).run()
            chunk = Compiler(tokens).compile()
        except (ScanError, ParseError, CompileError) as error:
            return report_error(error)

        if debug:
            print(raw_bytes(chunk), end="")
            print(disassemble(chunk), end="")

        try:
            VM(chunk).run()
        except VMRuntimeError as error:
            return report_error(error)
        return EXIT_OK

    try:
        program = Parser(Lexer(source).run()).parse()
        Interpreter().interpret(program)
    except (ScanError, ParseError) as error:
        return report_error(error)
    except LoxRuntimeError as error:
        return report_error(error)
    except RecursionError:
        print("[error] profundidad de recursión excedida", file=sys.stderr)
        return EXIT_RUNTIME

    return EXIT_OK


def report_error(error: Exception) -> int:
    """Imprime el error recibido en stderr y devuelve el código de salida."""
    if isinstance(error, (ScanError, ParseError)):
        print(f"[error] {error}", file=sys.stderr)
        return EXIT_SCAN_PARSE

    if isinstance(error, CompileError):
        if error.token is not None:
            print(
                f"[error] {error} (línea {error.token.line}, columna {error.token.column})",
                file=sys.stderr,
            )
        else:
            print(f"[error] {error}", file=sys.stderr)
        return EXIT_SCAN_PARSE

    if isinstance(error, (LoxRuntimeError, VMRuntimeError)):
        token = getattr(error, "token", None)
        if token is not None:
            print(
                f"[error] {error} (línea {token.line}, columna {token.column})",
                file=sys.stderr,
            )
        else:
            print(f"[error] {error} (línea {error.line})", file=sys.stderr)
        return EXIT_RUNTIME

    print(f"[error] {error}", file=sys.stderr)
    return EXIT_USAGE


def repl(backend: str = "tree-walk", debug: bool = False) -> int:
    """Bucle interactivo que lee líneas de la entrada estándar y las ejecuta."""
    while True:
        try:
            source = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return EXIT_OK

        if not source.strip():
            continue

        run_actions(source, backend=backend, debug=debug)


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada de la CLI; orquesta los argumentos y el modo elegido."""
    parser = argparse.ArgumentParser(
        prog="mylox",
        description="Intérprete de Lox (TPLenguajes y Compiladores I, FIUBA)",
    )

    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--tokens", action="store_true", help="modo escaneo: imprime la lista de tokens")
    modes.add_argument("--tree", action="store_true", help="modo parseo: imprime el árbol de sintaxis abstracta")

    parser.add_argument("file", nargs="?", type=Path, help="archivo a interpretar; si no se pasa, se abre un REPL")
    parser.add_argument("--backend", choices=("tree-walk", "bytecode"), default="tree-walk", help="backend de ejecución (por defecto: tree-walk)")
    parser.add_argument("--debug", action="store_true", help="muestra el bytecode generado (solo con --backend bytecode)")
    parser.add_argument("-v", "--version", action="version", version=f"mylox {__version__}")

    args = parser.parse_args(argv)

    if args.file is not None:
        try:
            source = args.file.read_text(encoding="utf-8")
        except OSError as error:
            print(f"[error] no se pudo leer el archivo: {error}", file=sys.stderr)
            return EXIT_USAGE
    else:
        return repl(backend=args.backend, debug=args.debug)

    if args.tokens:
        return run_tokens(source)
    if args.tree:
        return run_tree(source)
    return run_actions(source, backend=args.backend, debug=args.debug)


if __name__ == "__main__":
    sys.exit(main())
