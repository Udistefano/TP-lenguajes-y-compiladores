"""Máquina virtual que ejecuta un chunk de bytecode"""
from __future__ import annotations

from ..errors import VMRuntimeError
from ..tokens import LiteralValue
from ..values import is_equal, is_number, is_string, is_truthy, stringify
from .chunk import Chunk
from .disassembler import RUNTIME_HEADER
from .opcodes import OpCode


class VM:
    """Corre las instrucciones de un chunk sobre una pila de valores.  se lee el byte en ip y se ejecuta su
    lógica y avanza. No hay recursión ni nodos del AST, así que los resultados intermedios de las expresiones viven en stack
    """

    def __init__(self, chunk: Chunk) -> None:
        """Crea la máquina lista para ejecutar chunk, con la pila vacía."""
        self.chunk = chunk
        self.ip = 0
        self.stack: list[object] = []
        self.current_line = 1

    # Pila
    def push(self, value: object) -> None:
        """Agrega un valor al tope de la pila."""
        self.stack.append(value)

    def pop(self) -> object:
        """Devuelve el tope de la pila y lo retira."""
        if not self.stack:
            raise VMRuntimeError("STACK UNDERFLOW", line=self.current_line)
        return self.stack.pop()

    # Lectura del chunk
    def read_byte(self) -> int:
        """Consume el byte en la posición actual y avanza el puntero."""
        byte = self.chunk.read(self.ip)
        self.ip += 1
        return byte

    def read_constant(self) -> LiteralValue:
        """Consume un índice y devuelve la constante del pool que referencia."""
        return self.chunk.constant(self.read_byte())

    def run(self, trace: bool = False) -> None:
        """Consume instrucciones hasta OP_RETURN o el final del chunk."""
        if trace:
            print(RUNTIME_HEADER)

        while self.ip < len(self.chunk):
            start = self.ip
            self.current_line = self.chunk.line_at(self.ip)

            match OpCode(self.read_byte()):
                case OpCode.OP_CONSTANT:
                    self.push(self.read_constant())
                case OpCode.OP_TRUE:
                    self.push(True)
                case OpCode.OP_FALSE:
                    self.push(False)
                case OpCode.OP_NIL:
                    self.push(None)
                case OpCode.OP_POP:
                    self.pop()
                case OpCode.OP_PRINT:
                    value = self.pop()
                    if trace:
                        print(f"{start:04d}| SCREEN OUTPUT {stringify(value)}")
                        continue
                    print(stringify(value))
                case OpCode.OP_NEGATE:
                    value = self.pop()
                    if not is_number(value):
                        raise VMRuntimeError(
                            "Operand of - must be a number", line=self.current_line
                        )
                    self.push(-value)
                case OpCode.OP_NOT:
                    self.push(not is_truthy(self.pop()))
                case OpCode.OP_ADD:
                    right, left = self.pop(), self.pop()
                    if is_number(left) and is_number(right):
                        self.push(left + right)
                    elif is_string(left) and is_string(right):
                        self.push(left + right)
                    else:
                        raise VMRuntimeError(
                            "Operands of + must be either numbers or strings",
                            line=self.current_line,
                        )
                case OpCode.OP_SUBTRACT:
                    right, left = self.pop(), self.pop()
                    if not (is_number(left) and is_number(right)):
                        raise VMRuntimeError(
                            "Operands of - must be numbers", line=self.current_line
                        )
                    self.push(left - right)
                case OpCode.OP_MULTIPLY:
                    right, left = self.pop(), self.pop()
                    if not (is_number(left) and is_number(right)):
                        raise VMRuntimeError(
                            "Operands of * must be numbers", line=self.current_line
                        )
                    self.push(left * right)
                case OpCode.OP_DIVIDE:
                    right, left = self.pop(), self.pop()
                    if not (is_number(left) and is_number(right)):
                        raise VMRuntimeError(
                            "Operands of / must be numbers", line=self.current_line
                        )
                    if right == 0:
                        raise VMRuntimeError(
                            "Division by zero is not allowed", line=self.current_line
                        )
                    self.push(left / right)
                case OpCode.OP_MODULO:
                    right, left = self.pop(), self.pop()
                    if not (is_number(left) and is_number(right)):
                        raise VMRuntimeError(
                            "Operands of % must be numbers", line=self.current_line
                        )
                    if right == 0:
                        raise VMRuntimeError(
                            "Modulo by zero is not allowed", line=self.current_line
                        )
                    self.push(left % right)
                case OpCode.OP_EQUAL:
                    right, left = self.pop(), self.pop()
                    self.push(is_equal(left, right))
                case OpCode.OP_GREATER:
                    right, left = self.pop(), self.pop()
                    if not (is_number(left) and is_number(right)):
                        raise VMRuntimeError(
                            "Operands of > must be numbers", line=self.current_line
                        )
                    self.push(left > right)
                case OpCode.OP_LESS:
                    right, left = self.pop(), self.pop()
                    if not (is_number(left) and is_number(right)):
                        raise VMRuntimeError(
                            "Operands of < must be numbers", line=self.current_line
                        )
                    self.push(left < right)
                case OpCode.OP_RETURN:
                    if trace:
                        print(f"{start:04d}| THE END")
                    return
                case _:
                    raise VMRuntimeError(
                        f"UNKNOWN OPCODE {opcode.value}", line=self.current_line
                    )

            if trace:
                print(f"{start:04d}| STACK {self.stack}")
