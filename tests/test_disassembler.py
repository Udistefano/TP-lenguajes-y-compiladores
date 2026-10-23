import pytest

from mylox.bytecode.chunk import Chunk
from mylox.bytecode.disassembler import (
    BYTES_PER_LINE,
    COMPILETIME_HEADER,
    RAW_BYTES_HEADER,
    disassemble,
    disassemble_instruction,
    raw_bytes,
)
from mylox.bytecode.opcodes import OpCode


def chunk_de_expresion() -> Chunk:
    """El bytecode de 6 / 3 - 1; , armado a mano como en la diapositiva."""
    chunk = Chunk()
    seis = chunk.add_constant(6.0)
    chunk.emit(OpCode.OP_CONSTANT, line=1, operand=seis)
    tres = chunk.add_constant(3.0)
    chunk.emit(OpCode.OP_CONSTANT, line=1, operand=tres)
    chunk.emit(OpCode.OP_DIVIDE, line=1)
    uno = chunk.add_constant(1.0)
    chunk.emit(OpCode.OP_CONSTANT, line=1, operand=uno)
    chunk.emit(OpCode.OP_SUBTRACT, line=1)
    chunk.emit(OpCode.OP_POP, line=1)
    chunk.emit(OpCode.OP_RETURN, line=1)
    return chunk


def body(texto: str) -> list[str]:
    """Las líneas de una vista, sin el encabezado ni la línea final vacía."""
    return texto.strip().split("\n")[1:]



def test_los_offsets_se_muestran_con_cuatro_digitos():
    chunk = Chunk()
    for _ in range(3):
        chunk.emit(OpCode.OP_CONSTANT, line=1, operand=chunk.add_constant(1.0))

    offsets = [linea.split("|")[0] for linea in body(disassemble(chunk))]
    assert offsets == ["0000", "0002", "0004"]
    assert all(len(offset) == 4 for offset in offsets)


def test_op_constant_muestra_el_valor_y_no_el_indice():
    chunk = Chunk()
    chunk.emit(OpCode.OP_CONSTANT, line=1, operand=chunk.add_constant(42.0))

    assert body(disassemble(chunk)) == ["0000| OP_CONSTANT<42.0>"]


def test_las_cadenas_se_muestran_entre_comillas():
    chunk = Chunk()
    chunk.emit(OpCode.OP_CONSTANT, line=1, operand=chunk.add_constant("abc"))

    assert body(disassemble(chunk)) == ["0000| OP_CONSTANT<'abc'>"]


def test_una_instruccion_sin_operando_muestra_solo_su_nombre():
    chunk = Chunk()
    chunk.emit(OpCode.OP_ADD, line=1)

    assert body(disassemble(chunk)) == ["0000| OP_ADD"]


def test_el_listado_completo_coincide():
    esperado = [
        "0000| OP_CONSTANT<6.0>",
        "0002| OP_CONSTANT<3.0>",
        "0004| OP_DIVIDE",
        "0005| OP_CONSTANT<1.0>",
        "0007| OP_SUBTRACT",
        "0008| OP_POP",
        "0009| OP_RETURN",
    ]
    assert body(disassemble(chunk_de_expresion())) == esperado


def test_disassemble_instruction_avanza_un_byte_sin_operando():
    chunk = Chunk()
    chunk.emit(OpCode.OP_RETURN, line=1)
    chunk.emit(OpCode.OP_ADD, line=1)

    linea, siguiente = disassemble_instruction(chunk, 0)
    assert linea == "0000| OP_RETURN"
    assert siguiente == 1


def test_recorrer_el_chunk_no_deja_bytes_sin_cubrir():
    """La suma de los avances debe caer exactamente al final del chunk."""
    chunk = chunk_de_expresion()
    offset = 0
    instrucciones = 0
    while offset < len(chunk):
        _, offset = disassemble_instruction(chunk, offset)
        instrucciones += 1

    assert offset == len(chunk)
    assert instrucciones == 7



def vista_cruda_agrupa_bytes_y_separa_con_linea_vacia():
    chunk = Chunk()
    for _ in range(BYTES_PER_LINE + 2):
        chunk.emit(OpCode.OP_POP, line=1)

    lineas = raw_bytes(chunk).strip().split("\n")
    assert lineas[0] == RAW_BYTES_HEADER
    assert len(lineas[1].split()) == BYTES_PER_LINE
    assert lineas[2] == ""
    assert len(lineas[3].split()) == 2


def test_vista_cruda_describe_bytes_como_mide_chunk():
    chunk = chunk_de_expresion()
    crudos = [byte for linea in body(raw_bytes(chunk)) for byte in linea.split()]

    assert len(crudos) == len(chunk)


def test_chunk_vacio_produce_solo_encabezado():
    assert disassemble(Chunk()) == f"{COMPILETIME_HEADER}\n"
    assert raw_bytes(Chunk()) == f"{RAW_BYTES_HEADER}\n"

