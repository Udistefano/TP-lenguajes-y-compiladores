# Chunk: representación intermedia de un programa compilado a bytecode.

from __future__ import annotations

from collections.abc import Sequence

from ..errors import CompileError
from .opcodes import MAX_CONSTANT_INDEX, OpCode, takes_operand

# Un byte de código no puede representar valores fuera de este rango.
MIN_BYTE = 0
MAX_BYTE = 255


class Chunk:

    def __init__(self) -> None:
        """Crea un chunk vacío, sin instrucciones ni constantes."""
        self._bytes = bytearray()
        self._lines: list[int] = []
        self._constants: list[object] = []
        self._indices: dict[tuple[type, object], int] = {}


    #Escritura
    def write_byte(self, byte: int, line: int) -> None:
        """Agrega un byte al final del chunk y registra su línea de origen."""

        if not MIN_BYTE <= byte <= MAX_BYTE:
            raise CompileError(f"el valor {byte} no entra en un byte de código")

        self._bytes.append(byte)
        self._lines.append(line)

    def emit(self, opcode: OpCode, line: int, operand: int | None = None) -> None:
        """Emite una instrucción completa, con su operando si lo necesita."""

        if takes_operand(opcode):
            if operand is None:
                raise CompileError(f"{opcode.name} necesita un operando")
        elif operand is not None:
            raise CompileError(f"{opcode.name} no acepta operando")

        self.write_byte(opcode.value, line)
        if operand is not None:
            self.write_byte(operand, line)

    def add_constant(self, value: object) -> int:
        """Guarda ``value`` en el pool y devuelve el índice que lo referencia."""
        clave = (type(value), value)
        existente = self._indices.get(clave)
        if existente is not None:
            return existente

        if len(self._constants) > MAX_CONSTANT_INDEX:
            raise CompileError(
                "el programa tiene demasiadas constantes: se superaron las "
                f"{MAX_CONSTANT_INDEX + 1} entradas que permite OP_CONSTANT"
            )

        indice = len(self._constants)
        self._constants.append(value)
        self._indices[clave] = indice
        return indice

    # Lectura
    def read(self, offset: int) -> int:
        """Devuelve el byte en offset"""
        return self._bytes[offset]

    def line_at(self, offset: int) -> int:
        """Devuelve la línea de la fuente de la que salió el byte en offset"""
        return self._lines[offset]

    def constant(self, index: int) -> object:
        """Devuelve la constante del pool referenciada por index"""
        return self._constants[index]

    @property
    def constants(self) -> Sequence[object]:
        """El pool completo, en sólo lectura, para el desensamblador."""
        return tuple(self._constants)

    def patch(self, offset: int, byte: int) -> None:
        """Sobrescribe el byte en ``offset`` con un nuevo valor.

        Se usa para emparchar los placeholders de los saltos una vez que se
        conoce el offset real.
        """
        if not (0 <= offset < len(self._bytes)):
            raise CompileError(f"offset {offset} fuera de rango")
        if not (0 <= byte <= 255):
            raise CompileError(f"el byte {byte} no entra en un byte de código")
        self._bytes[offset] = byte

    def __len__(self) -> int:
        """Cantidad de bytes del chunk, que no equivale a cantidad de instrucciones."""
        return len(self._bytes)
