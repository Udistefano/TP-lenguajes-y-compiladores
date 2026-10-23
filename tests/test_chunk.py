import pytest

from mylox.bytecode.chunk import Chunk
from mylox.bytecode.opcodes import MAX_CONSTANT_INDEX, OpCode
from mylox.errors import CompileError


def test_una_instruccion_sin_operando_ocupa_un_byte():
    chunk = Chunk()
    chunk.emit(OpCode.OP_ADD, line=1)
    assert len(chunk) == 1
    assert chunk.read(0) == OpCode.OP_ADD.value


def test_op_constant_ocupa_dos_bytes():
    chunk = Chunk()
    indice = chunk.add_constant(6.0)
    chunk.emit(OpCode.OP_CONSTANT, line=1, operand=indice)

    assert len(chunk) == 2
    assert chunk.read(0) == OpCode.OP_CONSTANT.value
    assert chunk.read(1) == indice


def test_emit_con_operando_en_una_instruccion_que_no_acepta_falla():
    with pytest.raises(CompileError):
        Chunk().emit(OpCode.OP_ADD, line=1, operand=0)


def test_add_constant_devuelve_indices_correlativos():
    chunk = Chunk()
    assert chunk.add_constant(6.0) == 0
    assert chunk.add_constant(3.0) == 1
    assert chunk.add_constant(1.0) == 2


def test_add_constant_reutiliza_la_entrada_de_un_valor_repetido():
    chunk = Chunk()
    primero = chunk.add_constant(6.0)
    segundo = chunk.add_constant(6.0)

    assert primero == segundo
    assert len(chunk.constants) == 1


def test_add_constant_no_confunde_un_numero_con_true():
    chunk = Chunk()
    numero = chunk.add_constant(1.0)
    verdadero = chunk.add_constant(True)

    assert numero != verdadero
    assert chunk.constant(numero) == 1.0
    assert chunk.constant(verdadero) is True


def test_add_constant_distingue_una_cadena_de_un_numero():
    chunk = Chunk()
    assert chunk.add_constant("1") != chunk.add_constant(1.0)


def test_el_pool_no_supera_el_indice_maximo():
    chunk = Chunk()
    for valor in range(MAX_CONSTANT_INDEX + 1):
        chunk.add_constant(float(valor))

    assert len(chunk.constants) == MAX_CONSTANT_INDEX + 1
    with pytest.raises(CompileError):
        chunk.add_constant(float(MAX_CONSTANT_INDEX + 1))


def test_write_byte_fuera_de_rango_falla():
    chunk = Chunk()
    with pytest.raises(CompileError):
        chunk.write_byte(256, line=1)
    with pytest.raises(CompileError):
        chunk.write_byte(-1, line=1)


def test_un_chunk_empieza_vacio():
    assert len(Chunk()) == 0
    assert len(Chunk().constants) == 0


def test_line_at_registra_la_linea_de_cada_byte():
    chunk = Chunk()
    chunk.emit(OpCode.OP_CONSTANT, line=3, operand=chunk.add_constant(1.0))
    chunk.emit(OpCode.OP_ADD, line=4)

    # El operando pertenece a la misma línea que su instrucción.
    assert chunk.line_at(0) == 3
    assert chunk.line_at(1) == 3
    assert chunk.line_at(2) == 4


def test_el_bytecode_coincide_con_offsets_esperados():
    """El programa ``6 / 3 - 1;`` completo, con los offsets de la diapositiva."""
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

    assert len(chunk) == 10
    assert chunk.read(0) == OpCode.OP_CONSTANT.value
    assert chunk.read(1) == seis
    assert chunk.read(2) == OpCode.OP_CONSTANT.value
    assert chunk.read(3) == tres
    assert chunk.read(4) == OpCode.OP_DIVIDE.value
    assert chunk.read(5) == OpCode.OP_CONSTANT.value
    assert chunk.read(6) == uno
    assert chunk.read(7) == OpCode.OP_SUBTRACT.value
    assert chunk.read(8) == OpCode.OP_POP.value
    assert chunk.read(9) == OpCode.OP_RETURN.value


def test_constantes_quedan_en_el_pool():
    chunk = Chunk()
    for valor in (6.0, 3.0, 1.0):
        chunk.emit(OpCode.OP_CONSTANT, line=1, operand=chunk.add_constant(valor))

    assert list(chunk.constants) == [6.0, 3.0, 1.0]
    assert chunk.constant(0) == 6.0
    assert chunk.constant(2) == 1.0
