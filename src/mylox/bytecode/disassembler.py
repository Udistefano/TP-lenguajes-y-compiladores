"""Desensamblado de un chunk para el modo de depuración"""
from __future__ import annotations

from .chunk import Chunk
from .opcodes import OpCode, takes_operand

RAW_BYTES_HEADER = "== RAW BYTES =="
COMPILETIME_HEADER = "== COMPILETIME =="
RUNTIME_HEADER = "== RUNTIME =="

# Bytes por renglón de la vista cruda.
BYTES_PER_LINE = 5


def disassemble_instruction(chunk: Chunk, offset: int) -> tuple[str, int]:
    """Renderiza la instrucción en offset y devuelve el próximo offset"""
    opcode = OpCode(chunk.read(offset))

    # Saltos: operando de 2 bytes (offset).
    if opcode in (OpCode.OP_JUMP, OpCode.OP_JUMP_IF_FALSE, OpCode.OP_LOOP):
        high = chunk.read(offset + 1)
        low = chunk.read(offset + 2)
        target = (high << 8) | low
        if opcode == OpCode.OP_LOOP:
            return f"{offset:04d}| {opcode.name}<-{target}>", offset + 3
        return f"{offset:04d}| {opcode.name}<+{target}>", offset + 3

    # Funciones: OP_CALL lleva la cantidad de argumentos.
    if opcode == OpCode.OP_CALL:
        argc = chunk.read(offset + 1)
        return f"{offset:04d}| {opcode.name}<{argc}>", offset + 2

    # Upvalues: OP_GET_UPVALUE y OP_SET_UPVALUE llevan un índice de upvalue.
    if opcode in (OpCode.OP_GET_UPVALUE, OpCode.OP_SET_UPVALUE):
        slot = chunk.read(offset + 1)
        return f"{offset:04d}| {opcode.name}<{slot}>", offset + 2

    # OP_CLOSE_UPVALUE no lleva operando.
    if opcode == OpCode.OP_CLOSE_UPVALUE:
        return f"{offset:04d}| {opcode.name}", offset + 1

    # OP_CLOSURE lleva un índice del pool que referencia una función, seguido
    # de los upvalues que captura (is_local + slot por cada uno).
    if opcode == OpCode.OP_CLOSURE:
        function = chunk.constant(chunk.read(offset + 1))
        name = getattr(function, "name", None)
        display_name = name if name is not None else "script"
        upvalue_count = getattr(function, "upvalue_count", 0)
        return f"{offset:04d}| {opcode.name}<fn {display_name}()>", offset + 2 + 2 * upvalue_count

    # Instrucciones de variables globales: el operando es un índice del pool
    # que referencia el nombre de la variable.
    if opcode in (OpCode.OP_DEFINE_GLOBAL, OpCode.OP_GET_GLOBAL, OpCode.OP_SET_GLOBAL):
        name = chunk.constant(chunk.read(offset + 1))
        return f"{offset:04d}| {opcode.name}<{name!r}>", offset + 2

    if opcode in (OpCode.OP_CLASS, OpCode.OP_GET_PROPERTY, OpCode.OP_SET_PROPERTY,
                  OpCode.OP_METHOD, OpCode.OP_GET_SUPER):
        name = chunk.constant(chunk.read(offset + 1))
        return f"{offset:04d}| {opcode.name}<{name!r}>", offset + 2

    if opcode == OpCode.OP_INHERIT:
        return f"{offset:04d}| {opcode.name}", offset + 1

    # OP_INVOKE / OP_SUPER_INVOKE: nombre + cantidad de argumentos.
    if opcode in (OpCode.OP_INVOKE, OpCode.OP_SUPER_INVOKE):
        name = chunk.constant(chunk.read(offset + 1))
        argc = chunk.read(offset + 2)
        return f"{offset:04d}| {opcode.name}<{name!r}, {argc}>", offset + 3

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
