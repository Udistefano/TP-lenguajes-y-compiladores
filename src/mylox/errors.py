from __future__ import annotations
from .tokens import Token

class LoxError(Exception):
    """Error base de todo el intérprete."""


class ScanError(LoxError):
    """Error ocurrido durante el escaneo (análisis léxico)."""


class ParseError(LoxError):
    """Error ocurrido durante el parseo (análisis sintáctico)."""


class CompileError(LoxError):
    """Error ocurrido durante la compilación a bytecode."""
    def __init__(self, message: str, token: Token | None = None) -> None:
        self.token = token
        super().__init__(message)


class LoxRuntimeError(LoxError):
    """Error ocurrido durante la ejecución del programa."""

    def __init__(self, token: Token, message: str) -> None:
        self.token = token
        super().__init__(message)


class VMRuntimeError(LoxError):
    """Error ocurrido al ejecutar bytecode en la máquina virtual.
    """

    def __init__(self, message: str, line: int = 1) -> None:
        self.line = line
        super().__init__(message)
