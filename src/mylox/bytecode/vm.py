"""Máquina virtual que ejecuta un chunk de bytecode"""
from __future__ import annotations

from ..errors import VMRuntimeError
from ..lists import ListError, ListMethod, LoxList, require_list
from ..oop import LoxClass, LoxInstance
from ..values import is_equal, is_number, is_string, is_truthy, stringify
from .chunk import Chunk
from .disassembler import RUNTIME_HEADER
from .function import BoundMethod, CallFrame, Closure, Function, Upvalue
from .opcodes import OpCode

MAX_CALL_FRAMES = 1024

class VM:
    """Corre las instrucciones de un chunk sobre una pila de valores.

    La ejecución es un bucle lineal: se lee el byte en ``ip``, se ejecuta su
    lógica y se avanza. No hay recursión ni nodos del AST, así que los
    resultados intermedios de las expresiones viven en ``stack``.

    Cada invocación de función crea un ``CallFrame`` con su propio ``ip`` y
    su base en el stack, de modo que las variables locales se indexan de
    forma relativa a ese frame.
    """

    def __init__(self, chunk: Chunk) -> None:
        """Crea la máquina lista para ejecutar chunk, con la pila vacía."""
        self.main_chunk = chunk
        self.frames: list[CallFrame] = []
        self.stack: list[object] = []
        self.globals: dict[str, object] = {}
        self.open_upvalues: dict[int, Upvalue] = {}
        self.current_line = 1

    @property
    def chunk(self) -> Chunk:
        """El chunk del frame que se está ejecutando."""
        return self.frames[-1].closure.function.chunk

    @property
    def ip(self) -> int:
        """El ip del frame que se está ejecutando."""
        return self.frames[-1].ip

    @ip.setter
    def ip(self, value: int) -> None:
        self.frames[-1].ip = value

    # Pila
    def push(self, value: object) -> None:
        """Agrega un valor al tope de la pila."""
        self.stack.append(value)

    # Upvalues (closures)
    def capture_upvalue(self, stack_index: int) -> Upvalue:
        if stack_index not in self.open_upvalues:
            self.open_upvalues[stack_index] = Upvalue(stack_index)
        return self.open_upvalues[stack_index]

    def close_upvalues(self, first: int) -> None:
        for slot in [slot for slot in self.open_upvalues if slot >= first]:
            upvalue = self.open_upvalues.pop(slot)
            upvalue.closed_value = self.stack[slot]
            upvalue.stack_index = None

    def pop(self) -> object:
        """Devuelve el tope de la pila y lo retira."""
        if not self.stack:
            raise VMRuntimeError("STACK UNDERFLOW", line=self.current_line)
        return self.stack.pop()

    def peek(self, distance: int = 0) -> object:
        """Devuelve el valor a ``distance`` posiciones del tope, sin retirarlo."""
        if len(self.stack) <= distance:
            raise VMRuntimeError("STACK UNDERFLOW", line=self.current_line)
        return self.stack[-1 - distance]

    # Lectura del chunk
    def read_byte(self) -> int:
        """Consume el byte en la posición actual y avanza el puntero."""
        frame = self.frames[-1]
        byte = frame.closure.function.chunk.read(frame.ip)
        frame.ip += 1
        return byte

    def read_constant(self) -> object:
        """Consume un índice y devuelve la constante del pool que referencia."""
        return self.chunk.constant(self.read_byte())

    def call(self, callee: object, arg_count: int) -> None:
        base = len(self.stack) - arg_count - 1
        if isinstance(callee, ListMethod):
            if arg_count != callee.arity:
                raise VMRuntimeError(
                    f"Expected {callee.arity} arguments, got {arg_count}", line=self.current_line
                )
            result = callee.invoke(self.stack[base + 1:])
            del self.stack[base:]
            self.push(result)
            return
        if isinstance(callee, LoxClass):
            instance = LoxInstance(callee)
            initializer = callee.find_method("init")
            if initializer is None:
                if arg_count != 0:
                    raise VMRuntimeError(f"Expected 0 arguments, got {arg_count}", line=self.current_line)
                self.stack[base] = instance
                return
            self.stack[base] = instance
            closure = initializer
        elif isinstance(callee, BoundMethod):
            self.stack[base] = callee.instance
            closure = callee.method
        elif isinstance(callee, Closure):
            closure = callee
        else:
            raise VMRuntimeError("Can only call functions and classes.", line=self.current_line)
        if arg_count != closure.function.arity:
            raise VMRuntimeError(
                f"Expected {closure.function.arity} arguments, got {arg_count}", line=self.current_line
            )
        if len(self.frames) >= MAX_CALL_FRAMES:
            raise VMRuntimeError("Call stack limit exceeded", line=self.current_line)
        self.frames.append(CallFrame(closure, base))

    def run(self, trace: bool = False) -> None:
        try:
            self._run(trace)
        except ListError as error:
            raise VMRuntimeError(str(error), line=self.current_line) from None

    def _run(self, trace: bool = False) -> None:
        """Consume instrucciones hasta OP_RETURN o el final del chunk."""
        # Frame del script principal
        main_function = Function(None)
        main_function.chunk = self.main_chunk
        main_closure = Closure(main_function)
        main_frame = CallFrame(main_closure, 0)
        self.frames.append(main_frame)

        if trace:
            print(RUNTIME_HEADER)

        while self.frames:
            frame = self.frames[-1]
            chunk = frame.closure.function.chunk
            if frame.ip >= len(chunk):
                # Chunk agotado sin OP_RETURN: retorno implícito.
                finished_frame = self.frames.pop()
                self.close_upvalues(finished_frame.stack_slot)
                if not self.frames:
                    return
                del self.stack[finished_frame.stack_slot:]
                self.push(None)
                continue

            start = frame.ip
            self.current_line = chunk.line_at(frame.ip)

            match self.read_byte():
                case OpCode.OP_CONSTANT:
                    self.push(self.read_constant())
                case OpCode.OP_TRUE:
                    self.push(True)
                case OpCode.OP_FALSE:
                    self.push(False)
                case OpCode.OP_NIL:
                    self.push(None)
                case OpCode.OP_DEFINE_GLOBAL:
                    var_index = self.read_byte()
                    var_name = chunk.constant(var_index)
                    var_value = self.pop()
                    self.globals[str(var_name)] = var_value
                case OpCode.OP_SET_GLOBAL:
                    var_index = self.read_byte()
                    var_name = chunk.constant(var_index)
                    if str(var_name) not in self.globals:
                        raise VMRuntimeError(
                            f"Undefined variable '{var_name}'", line=self.current_line
                        )
                    self.globals[str(var_name)] = self.peek()
                case OpCode.OP_GET_GLOBAL:
                    var_index = self.read_byte()
                    var_name = chunk.constant(var_index)
                    if str(var_name) not in self.globals:
                        raise VMRuntimeError(
                            f"Undefined variable '{var_name}'", line=self.current_line
                        )
                    self.push(self.globals[str(var_name)])
                case OpCode.OP_GET_LOCAL:
                    slot = self.read_byte()
                    base = self.frames[-1].stack_slot
                    self.push(self.stack[base + slot])
                case OpCode.OP_SET_LOCAL:
                    slot = self.read_byte()
                    base = self.frames[-1].stack_slot
                    self.stack[base + slot] = self.peek()
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
                case OpCode.OP_JUMP:
                    offset = (self.read_byte() << 8) | self.read_byte()
                    frame.ip += offset
                case OpCode.OP_JUMP_IF_FALSE:
                    offset = (self.read_byte() << 8) | self.read_byte()
                    if not is_truthy(self.peek()):
                        frame.ip += offset
                case OpCode.OP_LOOP:
                    offset = (self.read_byte() << 8) | self.read_byte()
                    frame.ip -= offset
                case OpCode.OP_CALL:
                    arg_count = self.read_byte()
                    callee = self.peek(arg_count)
                    self.call(callee, arg_count)
                    if trace:
                        print(f"{start:04d}| CALL {callee}")
                    continue
                case OpCode.OP_CLOSURE:
                    fun_index = self.read_byte()
                    function = chunk.constant(fun_index)
                    closure = Closure(function)
                    self.push(closure)
                    for _ in range(function.upvalue_count):
                        is_local = self.read_byte() == 1
                        slot = self.read_byte()
                        if is_local:
                            stack_index = self.frames[-1].stack_slot + slot
                            upvalue = self.capture_upvalue(stack_index)
                        else:
                            upvalue = self.frames[-1].closure.upvalues[slot]
                        closure.upvalues.append(upvalue)
                case OpCode.OP_GET_UPVALUE:
                    slot = self.read_byte()
                    upvalue = self.frames[-1].closure.upvalues[slot]
                    if upvalue.stack_index is None:
                        self.push(upvalue.closed_value)
                    else:
                        self.push(self.stack[upvalue.stack_index])
                case OpCode.OP_SET_UPVALUE:
                    slot = self.read_byte()
                    upvalue = self.frames[-1].closure.upvalues[slot]
                    if upvalue.stack_index is None:
                        upvalue.closed_value = self.peek()
                    else:
                        self.stack[upvalue.stack_index] = self.peek()
                case OpCode.OP_CLOSE_UPVALUE:
                    self.close_upvalues(len(self.stack) - 1)
                    self.pop()
                case OpCode.OP_CLASS:
                    name = str(chunk.constant(self.read_byte()))
                    self.push(LoxClass(name, None, {}))
                case OpCode.OP_GET_PROPERTY:
                    name = str(chunk.constant(self.read_byte()))
                    obj = self.pop()
                    if isinstance(obj, LoxList):
                        self.push(obj.get_property(name))
                        continue
                    if not isinstance(obj, LoxInstance):
                        raise VMRuntimeError(
                            "Only instances have properties", line=self.current_line
                        )
                    if name in obj.fields:
                        self.push(obj.fields[name])
                    else:
                        method = obj.klass.find_method(name)
                        if isinstance(method, Closure):
                            self.push(BoundMethod(obj, method))
                        else:
                            raise VMRuntimeError(
                                f"Undefined property '{name}'.", line=self.current_line
                            )
                case OpCode.OP_SET_PROPERTY:
                    name = str(chunk.constant(self.read_byte()))
                    value = self.pop()
                    obj = self.pop()
                    if isinstance(obj, LoxList):
                        raise VMRuntimeError("List properties are read-only.", line=self.current_line)
                    if not isinstance(obj, LoxInstance):
                        raise VMRuntimeError(
                            "Only instances have fields", line=self.current_line
                        )
                    obj.fields[name] = value
                    self.push(value)
                case OpCode.OP_METHOD:
                    name = str(chunk.constant(self.read_byte()))
                    method = self.pop()
                    klass = self.peek()
                    if not isinstance(klass, LoxClass) or not isinstance(method, Closure):
                        raise VMRuntimeError(
                            "Invalid method definition", line=self.current_line
                        )
                    klass.methods[name] = method
                case OpCode.OP_INHERIT:
                    subclass = self.pop()
                    superclass = self.peek()
                    if not isinstance(superclass, LoxClass):
                        raise VMRuntimeError("Superclass must be a class", line=self.current_line)
                    subclass.superclass = superclass
                case OpCode.OP_GET_SUPER:
                    name = str(chunk.constant(self.read_byte()))
                    superclass = self.pop()
                    instance = self.pop()
                    method = superclass.find_method(name)
                    if method is None:
                        raise VMRuntimeError(f"Undefined property '{name}'.", line=self.current_line)
                    self.push(BoundMethod(instance, method))
                case OpCode.OP_LIST:
                    count = self.read_byte()
                    base = len(self.stack) - count
                    items = self.stack[base:]
                    del self.stack[base:]
                    self.push(LoxList(items))
                case OpCode.OP_GET_INDEX:
                    index = self.pop()
                    obj = require_list(self.pop())
                    self.push(obj.get(index))
                case OpCode.OP_SET_INDEX:
                    value = self.pop()
                    index = self.pop()
                    obj = require_list(self.pop())
                    self.push(obj.set(index, value))
                case OpCode.OP_RETURN:
                    result = self.pop()
                    finished_frame = self.frames.pop()
                    if finished_frame.closure.function.is_initializer:
                        # init descarta su valor y devuelve la instancia
                        # (que ocupa el slot 0 del frame que termina).
                        result = self.stack[finished_frame.stack_slot]
                    self.close_upvalues(finished_frame.stack_slot)
                    if not self.frames:
                        if trace:
                            print(f"{start:04d}| THE END")
                        return
                    del self.stack[finished_frame.stack_slot:]
                    self.push(result)
                    if trace:
                        print(f"{start:04d}| EXITING CALLFRAME {finished_frame.closure.function.name}()")
                        continue
                case _:
                    raise VMRuntimeError(
                        f"UNKNOWN OPCODE", line=self.current_line
                    )

            if trace:
                print(f"{start:04d}| STACK {self.stack}")
