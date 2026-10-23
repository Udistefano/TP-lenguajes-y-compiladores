import pytest

from mylox.bytecode.chunk import Chunk
from mylox.bytecode.opcodes import OpCode
from mylox.bytecode.vm import VM
from mylox.errors import VMRuntimeError


def ejecutar(chunk: Chunk) -> VM:
    """Corre el chunk en una VM nueva y devuelve la máquina ya ejecutada."""
    vm = VM(chunk)
    vm.run()
    return vm


def carga(chunk: Chunk, valor: float) -> None:
    """Emite una constante al chunk en la línea 1."""
    chunk.emit(OpCode.OP_CONSTANT, line=1, operand=chunk.add_constant(valor))


def test_resultado():
    chunk = Chunk()
    carga(chunk, 6.0)
    carga(chunk, 3.0)
    chunk.emit(OpCode.OP_DIVIDE, line=1)
    carga(chunk, 1.0)
    chunk.emit(OpCode.OP_SUBTRACT, line=1)

    assert ejecutar(chunk).stack == [1.0]


def test_pila_vacia_al_terminar_sentencia():
    chunk = Chunk()
    carga(chunk, 2.0)
    carga(chunk, 2.0)
    chunk.emit(OpCode.OP_MULTIPLY, line=1)
    chunk.emit(OpCode.OP_POP, line=1)

    assert ejecutar(chunk).stack == []


def test_orden_operandos():
    # 10 - 4: se popea 4 primero (derecha) y recién después 10 (izquierda).
    chunk = Chunk()
    carga(chunk, 10.0)
    carga(chunk, 4.0)
    chunk.emit(OpCode.OP_SUBTRACT, line=1)

    assert ejecutar(chunk).stack == [6.0]


def test_print_formato_lox(capsys):
    chunk = Chunk()
    carga(chunk, 6.0)
    chunk.emit(OpCode.OP_PRINT, line=1)
    chunk.emit(OpCode.OP_NIL, line=1)
    chunk.emit(OpCode.OP_PRINT, line=1)
    ejecutar(chunk)

    # Los enteros se muestran sin .0 y None como nil.
    assert capsys.readouterr().out == "6\nnil\n"


def test_op_return_detiene_ejecucion():
    chunk = Chunk()
    carga(chunk, 1.0)
    chunk.emit(OpCode.OP_RETURN, line=1)
    carga(chunk, 2.0)

    assert ejecutar(chunk).stack == [1.0]


def test_pop_pila_vacia_error_vm():
    chunk = Chunk()
    chunk.emit(OpCode.OP_POP, line=7)

    with pytest.raises(VMRuntimeError) as excinfo:
        ejecutar(chunk)

    assert "STACK UNDERFLOW" in str(excinfo.value)
    assert excinfo.value.line == 7
