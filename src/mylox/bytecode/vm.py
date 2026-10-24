"""Máquina virtual que ejecuta un chunk de bytecode"""
from __future__ import annotations

from ..errors import VMRuntimeError
from ..tokens import LiteralValue
from ..values import is_truthy, stringify
from .chunk import Chunk
from .opcodes import OpCode


class VM:
    """Corre las instrucciones de un chunk sobre una pila de valores.
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
        """Devuelve el tope de la pila y lo retira"""
        if not self.stack:
            raise VMRuntimeError("STACK UNDERFLOW", line=self.current_line)
        return self.stack.pop()

    # Lectura del chunk
    def read_byte(self) -> int:
        """Consume el byte en la posición actual y avanza el puntero"""
        byte = self.chunk.read(self.ip)
        self.ip += 1
        return byte

    def read_constant(self) -> LiteralValue:
        """Consume un índice y devuelve la constante del pool que referencia."""
        return self.chunk.constant(self.read_byte())

    def run(self) -> None:
        """Consume instrucciones hasta OP_RETURN o el final del chunk."""
        while self.ip < len(self.chunk):
            # La línea se lee antes de consumir el opcode: el op de una instrucción comparte línea con su código, así que sirve para
            # reportar cualquier error de esta instrucción.
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
                    print(stringify(self.pop()))
                case OpCode.OP_NEGATE:
                    self.push(-self.pop())
                case OpCode.OP_NOT:
                    self.push(not is_truthy(self.pop()))
                case OpCode.OP_ADD:
                    right, left = self.pop(), self.pop()
                    self.push(left + right)
                case OpCode.OP_SUBTRACT:
                    right, left = self.pop(), self.pop()
                    self.push(left - right)
                case OpCode.OP_MULTIPLY:
                    right, left = self.pop(), self.pop()
                    self.push(left * right)
                case OpCode.OP_DIVIDE:
                    right, left = self.pop(), self.pop()
                    self.push(left / right)
                case OpCode.OP_MODULO:
                    right, left = self.pop(), self.pop()
                    self.push(left % right)
                case OpCode.OP_EQUAL:
                    right, left = self.pop(), self.pop()
                    self.push(left == right)
                case OpCode.OP_GREATER:
                    right, left = self.pop(), self.pop()
                    self.push(left > right)
                case OpCode.OP_LESS:
                    right, left = self.pop(), self.pop()
                    self.push(left < right)
                case OpCode.OP_RETURN:
                    return
