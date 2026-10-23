"""Desensamblado de un chunk para el modo de depuración"""
from __future__ import annotations

from .chunk import Chunk
from .opcodes import OpCode, takes_operand

RAW_BYTES_HEADER = "== RAW BYTES =="
COMPILETIME_HEADER = "== COMPILETIME =="

# Bytes por renglón de la vista cruda.
BYTES_PER_LINE = 5


def disassemble_instruction(chunk: Chunk, offset: int) -> tuple[str, int]:
    """Renderiza la instrucción en offset y devuelve el próximo offset"""
    opcode = OpCode(chunk.read(offset))

    if not takes_operand(opcode):
        return f"{offset:04d}| {opcode.name}", offset + 1

    value = chunk.constant(chunk.read(offset + 1))
    return f"{offset:04d}| {opcode.name}<{value!r}>", offset + 2


def disassemble(chunk: Chunk) -> str:
    """Vista de tiempo de compilación: una línea por instrucción."""
    lines = [COMPILETIME_HEADER]
    offset = 0
    while offset < len(chunk):
        line, offset = disassemble_instruction(chunk, offset)
        lines.append(line)

    return "\n".join(lines) + "\n"


def raw_bytes(chunk: Chunk) -> str:
    """Vista cruda: cada byte del chunk en binario de 8 bits."""
    lines = [RAW_BYTES_HEADER]
    for start in range(0, len(chunk), BYTES_PER_LINE):
        if len(lines) > 1:
            lines.append("")
        end = min(start + BYTES_PER_LINE, len(chunk))
        lines.append(" ".join(f"{chunk.read(i):08b}" for i in range(start, end)))

    return "\n".join(lines) + "\n"
