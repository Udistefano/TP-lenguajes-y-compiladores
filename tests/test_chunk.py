import pytest

from mylox.bytecode.chunk import Chunk
from mylox.bytecode.opcodes import MAX_CONSTANT_INDEX, OpCode
from mylox.errors import CompileError


def test_emit_espacia_una_instruccion_sin_operando_y_dos_con_operando():
    chunk = Chunk()
    chunk.emit(OpCode.OP_ADD, line=1)
    assert len(chunk) == 1

    chunk.emit(OpCode.OP_CONSTANT, line=1, operand=0)
    assert len(chunk) == 3
    assert chunk.read(1) == OpCode.OP_CONSTANT.value


def test_emit_rechaza_un_operando_mal_usado():
    with pytest.raises(CompileError):
        Chunk().emit(OpCode.OP_CONSTANT, line=1)
    with pytest.raises(CompileError):
        Chunk().emit(OpCode.OP_ADD, line=1, operand=0)


def test_add_constant_devuelve_indices_correlativos():
    chunk = Chunk()
    assert (chunk.add_constant(6.0), chunk.add_constant(3.0)) == (0, 1)


def test_add_constant_reutiliza_un_valor_repetido():
    chunk = Chunk()
    assert chunk.add_constant(6.0) == chunk.add_constant(6.0)
    assert len(chunk.constants) == 1


def test_add_constant_no_confunde_un_numero_con_true():
    # En Python 1.0 == True; en Lox son tipos distintos y no pueden compartir
    # la entrada del pool.
    chunk = Chunk()
    numero = chunk.add_constant(1.0)
    verdadero = chunk.add_constant(True)

    assert numero != verdadero
    assert chunk.constant(verdadero) is True


def test_el_pool_no_supera_el_indice_maximo():
    chunk = Chunk()
    for valor in range(MAX_CONSTANT_INDEX + 1):
        chunk.add_constant(float(valor))

    with pytest.raises(CompileError):
        chunk.add_constant(float(MAX_CONSTANT_INDEX + 1))


def test_line_at_devuelve_la_linea_de_cada_byte():
    chunk = Chunk()
    chunk.emit(OpCode.OP_CONSTANT, line=3, operand=chunk.add_constant(1.0))
    chunk.emit(OpCode.OP_ADD, line=4)

    # El operando pertenece a la misma línea que su instrucción.
    assert (chunk.line_at(0), chunk.line_at(1), chunk.line_at(2)) == (3, 3, 4)


def test_el_bytecode_de_una_expresion_coincide_con_los_offsets_esperados():
    """El programa 6 / 3 - 1; completo, como en la diapositiva."""
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
    assert [chunk.read(i) for i in range(len(chunk))] == [
        OpCode.OP_CONSTANT.value, seis,
        OpCode.OP_CONSTANT.value, tres,
        OpCode.OP_DIVIDE.value,
        OpCode.OP_CONSTANT.value, uno,
        OpCode.OP_SUBTRACT.value,
        OpCode.OP_POP.value,
        OpCode.OP_RETURN.value,
    ]
