"""Máquina virtual que ejecuta un chunk de bytecode"""
from __future__ import annotations

from ..errors import VMRuntimeError
from ..oop import LoxClass, LoxInstance
from ..tokens import LiteralValue
from ..values import is_equal, is_number, is_string, is_truthy, stringify
from .chunk import Chunk
from .disassembler import RUNTIME_HEADER
from .function import BoundMethod, CallFrame, Closure, Function, Upvalue
from .opcodes import OpCode


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
        self.open_upvalues: list = []
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
    def capture_upvalue(self, stack_index: int):
        """Asegura que exista un upvalue abierto para stack_index."""
        for upvalue in self.open_upvalues:
            if upvalue.stack_index == stack_index:
                return upvalue

        created = Upvalue(stack_index)
        insert_pos = len(self.open_upvalues)
        for i, upvalue in enumerate(self.open_upvalues):
            if upvalue.stack_index is None or upvalue.stack_index > stack_index:
                insert_pos = i
                break
        self.open_upvalues.insert(insert_pos, created)
        return created

    def close_upvalues(self, last: int) -> None:
        """Cierra todos los upvalues que vivan en posiciones >= last."""
        while self.open_upvalues:
            upvalue = self.open_upvalues[0]
            if upvalue.stack_index is not None and upvalue.stack_index >= last:
                upvalue.closed_value = self.stack[upvalue.stack_index]
                upvalue.stack_index = None
                self.open_upvalues.pop(0)
            else:
                break

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
        byte = self.chunk.read(self.ip)
        self.ip += 1
        return byte

    def read_constant(self) -> LiteralValue:
        """Consume un índice y devuelve la constante del pool que referencia."""
        return self.chunk.constant(self.read_byte())

    def run(self, trace: bool = False) -> None:
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
            if self.ip >= len(self.chunk):
                # Chunk agotado sin OP_RETURN: retorno implícito.
                finished_frame = self.frames.pop()
                if not self.frames:
                    return
                self.stack = self.stack[: finished_frame.stack_slot - 1]
                self.push(None)
                continue

            start = self.ip
            self.current_line = self.chunk.line_at(self.ip) if self.ip < len(self.chunk) else 1

            match OpCode(self.read_byte()):
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
                    var_name = self.chunk.constant(var_index)
                    var_value = self.pop()
                    self.globals[str(var_name)] = var_value
                case OpCode.OP_SET_GLOBAL:
                    var_index = self.read_byte()
                    var_name = self.chunk.constant(var_index)
                    if str(var_name) not in self.globals:
                        raise VMRuntimeError(
                            f"Undefined variable '{var_name}'", line=self.current_line
                        )
                    self.globals[str(var_name)] = self.peek()
                case OpCode.OP_GET_GLOBAL:
                    var_index = self.read_byte()
                    var_name = self.chunk.constant(var_index)
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
                    self.ip += offset
                case OpCode.OP_JUMP_IF_FALSE:
                    offset = (self.read_byte() << 8) | self.read_byte()
                    if not is_truthy(self.peek()):
                        self.ip += offset
                case OpCode.OP_LOOP:
                    offset = (self.read_byte() << 8) | self.read_byte()
                    self.ip -= offset
                case OpCode.OP_CALL:
                    arg_count = self.read_byte()
                    callee = self.peek(arg_count)
                    if isinstance(callee, LoxClass):
                        # Instanciación: reemplaza la clase por la instancia
                        instance = LoxInstance(callee)
                        initializer = callee.find_method("init")
                        if isinstance(initializer, Closure):
                            if initializer.function.arity != arg_count:
                                raise VMRuntimeError(
                                    f"Expected {initializer.function.arity} arguments, "
                                    f"got {arg_count}",
                                    line=self.current_line,
                                )
                            self.stack[-arg_count - 1] = instance
                            self.frames[-1].ip = self.ip
                            self.frames.append(
                                CallFrame(initializer, len(self.stack) - arg_count - 1)
                            )
                            self.ip = 0
                            if trace:
                                print(
                                    f"{start:04d}| ENTERING CALLFRAME "
                                    f"{callee.name}.init()"
                                )
                            continue
                        if arg_count != 0:
                            raise VMRuntimeError(
                                f"Expected 0 arguments, got {arg_count} "
                                f"for class '{callee.name}'",
                                line=self.current_line,
                            )
                        self.stack[-arg_count - 1] = instance
                        if arg_count:
                            del self.stack[-arg_count:]
                        continue
                    if isinstance(callee, BoundMethod):
                        # El método ligado deja su instancia en el slot 0 del
                        # nuevo frame: ahí el compilador declaró ``this``.
                        closure = callee.method
                        self.stack[-arg_count - 1] = callee.instance
                    elif isinstance(callee, Closure):
                        closure = callee
                    else:
                        raise VMRuntimeError(
                            f"Cannot call non-callable object: {callee}",
                            line=self.current_line,
                        )
                    if closure.function.arity != arg_count:
                        raise VMRuntimeError(
                            f"Expected {closure.function.arity} arguments, got {arg_count}",
                            line=self.current_line,
                        )
                    self.frames[-1].ip = self.ip
                    fn_callframe = CallFrame(closure, len(self.stack) - arg_count - 1)
                    self.frames.append(fn_callframe)
                    self.ip = 0
                    if trace:
                        print(f"{start:04d}| ENTERING CALLFRAME {closure.function.name}()")
                        continue
                case OpCode.OP_CLOSURE:
                    fun_index = self.read_byte()
                    function = self.chunk.constant(fun_index)
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
                    name = str(self.chunk.constant(self.read_byte()))
                    self.push(LoxClass(name, None, {}))
                case OpCode.OP_GET_PROPERTY:
                    name = str(self.chunk.constant(self.read_byte()))
                    obj = self.pop()
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
                    name = str(self.chunk.constant(self.read_byte()))
                    value = self.pop()
                    obj = self.pop()
                    if not isinstance(obj, LoxInstance):
                        raise VMRuntimeError(
                            "Only instances have fields", line=self.current_line
                        )
                    obj.fields[name] = value
                    self.push(value)
                case OpCode.OP_METHOD:
                    name = str(self.chunk.constant(self.read_byte()))
                    method = self.pop()
                    klass = self.peek()
                    if not isinstance(klass, LoxClass) or not isinstance(method, Closure):
                        raise VMRuntimeError(
                            "Invalid method definition", line=self.current_line
                        )
                    klass.methods[name] = method
                case OpCode.OP_INHERIT:
                    # El stack tiene [superclass, subclass]: la subclase fue
                    # empujada despues por OP_CLASS.
                    subclass = self.pop()
                    superclass = self.pop()
                    if not isinstance(superclass, LoxClass):
                        raise VMRuntimeError(
                            "Superclass must be a class", line=self.current_line
                        )
                    if not isinstance(subclass, LoxClass):
                        raise VMRuntimeError(
                            "Invalid inherit target", line=self.current_line
                        )
                    subclass.superclass = superclass
                    self.push(subclass)
                case OpCode.OP_GET_SUPER:
                    name = str(self.chunk.constant(self.read_byte()))
                    this_value = self.stack[self.frames[-1].stack_slot]
                    if not isinstance(this_value, LoxInstance):
                        raise VMRuntimeError(
                            "super is only allowed inside a method",
                            line=self.current_line,
                        )
                    # La superclase se resuelve lexicamente respecto de la clase
                    # en la que el método está definido, no respecto de la clase
                    # real de la instancia (que puede ser una subclase).
                    defining_class_name = self.frames[-1].closure.function.enclosing_class
                    defining_class = this_value.klass
                    if defining_class_name is not None and defining_class_name in self.globals:
                        candidate = self.globals[defining_class_name]
                        if isinstance(candidate, LoxClass):
                            defining_class = candidate
                    superclass = defining_class.superclass
                    if not isinstance(superclass, LoxClass):
                        raise VMRuntimeError(
                            "No superclass to call super from",
                            line=self.current_line,
                        )
                    method = superclass.find_method(name)
                    if not isinstance(method, Closure):
                        raise VMRuntimeError(
                            f"Undefined property '{name}'.", line=self.current_line
                        )
                    self.push(BoundMethod(this_value, method))
                case OpCode.OP_RETURN:
                    result = self.pop()
                    finished_frame = self.frames.pop()
                    if finished_frame.closure.function.is_initializer:
                        # init descarta su valor y devuelve la instancia
                        # (que ocupa el slot 0 del frame que termina).
                        result = self.stack[finished_frame.stack_slot]
                    self.close_upvalues(finished_frame.stack_slot - 1)
                    if not self.frames:
                        if trace:
                            print(f"{start:04d}| THE END")
                        return
                    self.stack = self.stack[: finished_frame.stack_slot]
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
