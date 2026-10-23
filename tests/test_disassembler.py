from mylox.bytecode.chunk import Chunk
from mylox.bytecode.disassembler import (
    COMPILETIME_HEADER,
    RAW_BYTES_HEADER,
    disassemble,
    disassemble_instruction,
    raw_bytes,
)
from mylox.bytecode.opcodes import OpCode


def chunk_de_expresion() -> Chunk:
    """El bytecode de 6 / 3 - 1; , armado a mano."""
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
    """Las líneas de una vista, sin el encabezado."""
    return texto.strip().split("\n")[1:]


def test_el_listado_completo_coincide_con_la_diapositiva():
    assert body(disassemble(chunk_de_expresion())) == [
        "0000| OP_CONSTANT<6.0>",
        "0002| OP_CONSTANT<3.0>",
        "0004| OP_DIVIDE",
        "0005| OP_CONSTANT<1.0>",
        "0007| OP_SUBTRACT",
        "0008| OP_POP",
        "0009| OP_RETURN",
    ]


def test_op_constant_muestra_el_valor_y_las_cadenas_van_entre_comillas():
    chunk = Chunk()
    chunk.emit(OpCode.OP_CONSTANT, line=1, operand=chunk.add_constant("abc"))

    assert body(disassemble(chunk)) == ["0000| OP_CONSTANT<'abc'>"]


def test_disassemble_instruction_devuelve_el_proximo_offset():
    # Una instrucción con operando ocupa dos bytes y la siguiente sigue ahí.
    chunk = Chunk()
    chunk.emit(OpCode.OP_CONSTANT, line=1, operand=chunk.add_constant(6.0))
    chunk.emit(OpCode.OP_RETURN, line=1)

    assert disassemble_instruction(chunk, 0) == ("0000| OP_CONSTANT<6.0>", 2)
    assert disassemble_instruction(chunk, 2) == ("0002| OP_RETURN", 3)


def test_recorrer_el_chunk_no_deja_bytes_sin_cubrir():
    chunk = chunk_de_expresion()
    offset = 0
    instrucciones = 0
    while offset < len(chunk):
        _, offset = disassemble_instruction(chunk, offset)
        instrucciones += 1

    assert offset == len(chunk)
    assert instrucciones == 7


def test_la_vista_cruda_describe_tantos_bytes_como_mide_el_chunk():
    chunk = chunk_de_expresion()
    crudos = [byte for linea in body(raw_bytes(chunk)) for byte in linea.split()]

    assert len(crudos) == len(chunk)
    assert all(len(byte) == 8 for byte in crudos)


def test_un_chunk_vacio_produce_solo_el_encabezado():
    assert disassemble(Chunk()) == f"{COMPILETIME_HEADER}\n"
    assert raw_bytes(Chunk()) == f"{RAW_BYTES_HEADER}\n"
