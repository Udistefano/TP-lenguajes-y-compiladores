"""Compilador de Lox a bytecode, de una sola pasada"""
from __future__ import annotations

from ..errors import ParseError
from ..tokens import Token, TokenKind
from .chunk import Chunk
from .function import Function
from .opcodes import OpCode


class Local:
    """Una variable local durante la compilación.

    ``depth`` indica el nivel de anidación del scope que la declaró.
    ``initialized`` evita leer la variable en su propia inicialización.
    ``is_captured`` indica si algún closure capturó esta variable: al cerrar
    el scope se emite OP_CLOSE_UPVALUE en vez de OP_POP.
    """

    def __init__(self, name: str, depth: int) -> None:
        self.name = name
        self.depth = depth
        self.initialized = False
        self.is_captured = False


class Compiler:
    """Traduce una secuencia de tokens en un chunk de bytecode. No construye AST: parsea y emite instrucciones en el mismo recorrido
    """

    def __init__(self, tokens: list[Token], start: int = 0, enclosing=None) -> None:
        """Conserva la secuencia de tokens e inicia el cursor y el chunk."""
        self.tokens = tokens
        self.current = start
        self.chunk = Chunk()
        self.scope_depth = 0
        self.locals: list[Local] = []
        self.in_function = False
        self.in_method = False
        self.in_class = False
        self.has_superclass = False
        self.enclosing = enclosing
        self.upvalues: list[tuple[bool, int]] = []

    # ---------- Scopes ---------- #

    def begin_scope(self) -> None:
        """Entra a un bloque nuevo, incrementando la profundidad de scope."""
        self.scope_depth += 1

    def end_scope(self) -> None:
        """Sale del bloque actual y retira las variables locales del stack."""
        self.scope_depth -= 1
        removed = 0
        while self.locals and self.locals[-1].depth > self.scope_depth:
            removed += 1
            local = self.locals.pop()
            if local.is_captured:
                self.chunk.emit(OpCode.OP_CLOSE_UPVALUE, self.previous().line)
            else:
                self.chunk.emit(OpCode.OP_POP, self.previous().line)

    def declare(self, name: str) -> None:
        """Registra una variable local en el scope actual."""
        if self.scope_depth == 0:
            return
        for local in reversed(self.locals):
            if local.depth < self.scope_depth:
                break
            if local.name == name:
                raise ParseError(f"Variable {name} ya existe en este ámbito")
        self.locals.append(Local(name, self.scope_depth))

    def mark_initialized(self) -> None:
        """Marca la última variable local declarada como inicializada."""
        if self.locals:
            self.locals[-1].initialized = True

    def resolve_local(self, name: Token) -> int | None:
        """Devuelve el slot de la variable local, o None si es global."""
        for idx, local in enumerate(reversed(self.locals), 1):
            if local.name == name.lexeme:
                if not local.initialized:
                    raise ParseError(
                        f"No se puede leer la variable local en su propia "
                        f"inicialización en la línea {name.line}, columna {name.column}"
                    )
                return len(self.locals) - idx
        return None

    def resolve_upvalue(self, name: Token) -> int | None:
        """Busca la variable en los scopes exteriores. Si la encuentra, la
        registra como upvalue del compilador actual y devuelve su índice."""
        if self.enclosing is None:
            return None

        slot = self.enclosing.resolve_local(name)
        if slot is not None:
            # Marcar el local como capturado
            self.enclosing.locals[slot].is_captured = True
            return self.add_upvalue(slot, is_local=True)

        upvalue_index = self.enclosing.resolve_upvalue(name)
        if upvalue_index is not None:
            return self.add_upvalue(upvalue_index, is_local=False)

        return None

    def add_upvalue(self, slot: int, is_local: bool) -> int:
        """Registra un upvalue y devuelve su índice en la lista."""
        for idx, (local, s) in enumerate(self.upvalues):
            if local == is_local and s == slot:
                return idx
        self.upvalues.append((is_local, slot))
        return len(self.upvalues) - 1

    def compile(self) -> Chunk:
        """Compila un programa completo y devuelve el chunk resultante."""
        while not self.is_at_end():
            self.declaration()
        self.chunk.emit(OpCode.OP_NIL, self.previous().line)
        self.chunk.emit(OpCode.OP_RETURN, self.previous().line)
        return self.chunk

    # Declaraciones
    def declaration(self) -> None:
        """Lee una declaración class, var, fun o delega en una sentencia."""
        if self.match(TokenKind.CLASS):
            self.class_declaration()
        elif self.match(TokenKind.FUN):
            self.function_declaration()
        elif self.match(TokenKind.VAR):
            self.var_declaration()
        else:
            self.statement()

    def var_declaration(self) -> None:
        """Compila ``var nombre (= expresión)? ;``."""
        name = self.consume(TokenKind.IDENTIFIER, "Se esperaba un nombre de variable")
        is_local = self.scope_depth > 0

        if is_local:
            self.declare(name.lexeme)

        if self.match(TokenKind.EQUAL):
            self.expression()
        else:
            self.chunk.emit(OpCode.OP_NIL, name.line)

        self.consume(TokenKind.SEMICOLON, "Se esperaba ';' después de var")

        if is_local:
            self.mark_initialized()
        else:
            index = self.chunk.add_constant(name.lexeme)
            self.chunk.emit(OpCode.OP_DEFINE_GLOBAL, name.line, index)

    def if_statement(self) -> None:
        """Compila ``if (condición) sentencia (else sentencia)?``."""
        self.consume(TokenKind.LEFT_PAREN, "Se esperaba '(' después de if")
        self.expression()
        self.consume(TokenKind.RIGHT_PAREN, "Se esperaba ')' después de la condición")

        then_jump = self.emit_jump(OpCode.OP_JUMP_IF_FALSE, self.previous().line)
        self.chunk.emit(OpCode.OP_POP, self.previous().line)

        self.statement()

        else_jump = self.emit_jump(OpCode.OP_JUMP, self.previous().line)
        self.patch_jump(then_jump)
        self.chunk.emit(OpCode.OP_POP, self.previous().line)

        if self.match(TokenKind.ELSE):
            self.statement()

        self.patch_jump(else_jump)

    def while_statement(self) -> None:
        """Compila ``while (condición) sentencia``."""
        loop_start = len(self.chunk)
        self.consume(TokenKind.LEFT_PAREN, "Se esperaba '(' después de while")
        self.expression()
        self.consume(TokenKind.RIGHT_PAREN, "Se esperaba ')' después de la condición")

        exit_jump = self.emit_jump(OpCode.OP_JUMP_IF_FALSE, self.previous().line)
        self.chunk.emit(OpCode.OP_POP, self.previous().line)

        self.statement()

        self.emit_loop(loop_start, self.previous().line)
        self.patch_jump(exit_jump)
        self.chunk.emit(OpCode.OP_POP, self.previous().line)

    def for_statement(self) -> None:
        """Compila ``for (init; cond; incr) sentencia``."""
        self.begin_scope()
        self.consume(TokenKind.LEFT_PAREN, "Se esperaba '(' después de for")

        # Inicializador
        if self.match(TokenKind.SEMICOLON):
            pass
        elif self.match(TokenKind.VAR):
            self.var_declaration()
        else:
            self.expression()
            self.consume(TokenKind.SEMICOLON, "Se esperaba ';' después de la expresión")
            self.chunk.emit(OpCode.OP_POP, self.previous().line)

        # Condición
        loop_start = len(self.chunk)
        exit_jump = None
        if not self.check(TokenKind.SEMICOLON):
            self.expression()
            self.consume(TokenKind.SEMICOLON, "Se esperaba ';' después de la condición")
            exit_jump = self.emit_jump(OpCode.OP_JUMP_IF_FALSE, self.previous().line)
            self.chunk.emit(OpCode.OP_POP, self.previous().line)
        else:
            self.consume(TokenKind.SEMICOLON, "Se esperaba ';' después de la condición")

        # Incremento
        if not self.check(TokenKind.RIGHT_PAREN):
            body_jump = self.emit_jump(OpCode.OP_JUMP, self.previous().line)
            increment_start = len(self.chunk)
            self.expression()
            self.chunk.emit(OpCode.OP_POP, self.previous().line)
            self.consume(TokenKind.RIGHT_PAREN, "Se esperaba ')' después de las cláusulas")
            self.emit_loop(loop_start, self.previous().line)
            loop_start = increment_start
            self.patch_jump(body_jump)
        else:
            self.consume(TokenKind.RIGHT_PAREN, "Se esperaba ')' después de las cláusulas")

        # Cuerpo
        self.statement()
        self.emit_loop(loop_start, self.previous().line)

        if exit_jump is not None:
            self.patch_jump(exit_jump)
            self.chunk.emit(OpCode.OP_POP, self.previous().line)

        self.end_scope()

    def function_declaration(self) -> None:
        """Compila ``fun nombre ( params? ) { cuerpo }``."""
        name = self.consume(TokenKind.IDENTIFIER, "Se esperaba un nombre de función")
        is_local = self.scope_depth > 0

        if is_local:
            self.declare(name.lexeme)
            self.mark_initialized()

        self.consume(TokenKind.LEFT_PAREN, "Se esperaba '(' después del nombre")

        params: list[Token] = []
        if not self.check(TokenKind.RIGHT_PAREN):
            params.append(self.consume(TokenKind.IDENTIFIER, "Se esperaba un parámetro"))
            while self.match(TokenKind.COMMA):
                params.append(self.consume(TokenKind.IDENTIFIER, "Se esperaba un parámetro"))

        self.consume(TokenKind.RIGHT_PAREN, "Se esperaba ')' después de los parámetros")
        self.consume(TokenKind.LEFT_BRACE, "Se esperaba '{' antes del cuerpo")

        body_compiler = Compiler(self.tokens, start=self.current, enclosing=self)
        body_compiler.in_function = True
        body_compiler.begin_scope()

        # Slot 0: la función misma (normal) o this (método).
        if body_compiler.in_method:
            body_compiler.declare("this")
        else:
            body_compiler.declare("_")
        body_compiler.mark_initialized()

        for param in params:
            body_compiler.declare(param.lexeme)
            body_compiler.mark_initialized()

        while not body_compiler.is_at_end() and not body_compiler.check(TokenKind.RIGHT_BRACE):
            body_compiler.declaration()

        body_compiler.consume(TokenKind.RIGHT_BRACE, "Se esperaba '}' después del cuerpo")

        # Failsafe return
        body_compiler.chunk.emit(OpCode.OP_NIL, body_compiler.previous().line)
        body_compiler.chunk.emit(OpCode.OP_RETURN, body_compiler.previous().line)

        self.current = body_compiler.current

        function = Function(name.lexeme)
        function.chunk = body_compiler.chunk
        function.arity = len(params)
        function.upvalue_count = len(body_compiler.upvalues)
        index = self.chunk.add_constant(function)
        self.chunk.emit(OpCode.OP_CLOSURE, name.line, index)

        # Emitir los upvalues capturados
        for is_local, slot in body_compiler.upvalues:
            self.chunk.write_byte(1 if is_local else 0, name.line)
            self.chunk.write_byte(slot, name.line)

        if not is_local:
            name_index = self.chunk.add_constant(name.lexeme)
            self.chunk.emit(OpCode.OP_DEFINE_GLOBAL, name.line, name_index)

    def class_declaration(self) -> None:
        """Compila ``class nombre ( < superclase )? { métodos }``."""
        name = self.consume(TokenKind.IDENTIFIER, "Se esperaba un nombre de clase")
        has_superclass = False

        if self.match(TokenKind.LESS):
            has_superclass = True
            superclass_name = self.consume(TokenKind.IDENTIFIER, "Se esperaba nombre de superclase")
            slot = self.resolve_local(superclass_name)
            if slot is not None:
                self.chunk.emit(OpCode.OP_GET_LOCAL, superclass_name.line, slot)
            else:
                upvalue_index = self.resolve_upvalue(superclass_name)
                if upvalue_index is not None:
                    self.chunk.emit(OpCode.OP_GET_UPVALUE, superclass_name.line, upvalue_index)
                else:
                    index = self.chunk.add_constant(superclass_name.lexeme)
                    self.chunk.emit(OpCode.OP_GET_GLOBAL, superclass_name.line, index)

        index = self.chunk.add_constant(name.lexeme)
        self.chunk.emit(OpCode.OP_CLASS, name.line, index)

        if has_superclass:
            self.chunk.emit(OpCode.OP_INHERIT, name.line)

        self.consume(TokenKind.LEFT_BRACE, "Se esperaba '{' después del nombre")

        while not self.check(TokenKind.RIGHT_BRACE) and not self.is_at_end():
            self.method_declaration()

        self.consume(TokenKind.RIGHT_BRACE, "Se esperaba '}' después de la clase")

        self.chunk.emit(OpCode.OP_POP, name.line)

        if self.scope_depth == 0:
            name_index = self.chunk.add_constant(name.lexeme)
            self.chunk.emit(OpCode.OP_DEFINE_GLOBAL, name.line, name_index)
        else:
            slot = self.resolve_local(name)
            if slot is not None:
                self.chunk.emit(OpCode.OP_SET_LOCAL, name.line, slot)
            else:
                name_index = self.chunk.add_constant(name.lexeme)
                self.chunk.emit(OpCode.OP_DEFINE_GLOBAL, name.line, name_index)

    def method_declaration(self) -> None:
        """Compila un método de clase (sin keyword fun)."""
        name = self.consume(TokenKind.IDENTIFIER, "Se esperaba un nombre de método")
        had_method = self.in_method
        self.in_method = True

        self.consume(TokenKind.LEFT_PAREN, "Se esperaba '(' después del nombre")

        params: list[Token] = []
        if not self.check(TokenKind.RIGHT_PAREN):
            params.append(self.consume(TokenKind.IDENTIFIER, "Se esperaba un parámetro"))
            while self.match(TokenKind.COMMA):
                params.append(self.consume(TokenKind.IDENTIFIER, "Se esperaba un parámetro"))

        self.consume(TokenKind.RIGHT_PAREN, "Se esperaba ')' después de los parámetros")
        self.consume(TokenKind.LEFT_BRACE, "Se esperaba '{' antes del cuerpo")

        body_compiler = Compiler(self.tokens, start=self.current, enclosing=self)
        body_compiler.in_function = True
        body_compiler.in_method = True
        body_compiler.begin_scope()

        # this es slot 0
        body_compiler.declare("this")
        body_compiler.mark_initialized()

        for param in params:
            body_compiler.declare(param.lexeme)
            body_compiler.mark_initialized()

        while not body_compiler.is_at_end() and not body_compiler.check(TokenKind.RIGHT_BRACE):
            body_compiler.declaration()

        body_compiler.consume(TokenKind.RIGHT_BRACE, "Se esperaba '}' después del cuerpo")

        body_compiler.chunk.emit(OpCode.OP_NIL, body_compiler.previous().line)
        body_compiler.chunk.emit(OpCode.OP_RETURN, body_compiler.previous().line)

        self.current = body_compiler.current

        function = Function(name.lexeme)
        function.chunk = body_compiler.chunk
        function.arity = len(params)
        function.upvalue_count = len(body_compiler.upvalues)
        index = self.chunk.add_constant(function)
        self.chunk.emit(OpCode.OP_CLOSURE, name.line, index)

        for is_local, slot in body_compiler.upvalues:
            self.chunk.write_byte(1 if is_local else 0, name.line)
            self.chunk.write_byte(slot, name.line)

        name_index = self.chunk.add_constant(name.lexeme)
        self.chunk.emit(OpCode.OP_METHOD, name.line, name_index)

        self.in_method = had_method

    # Sentencias

    def statement(self) -> None:
        """Lee una sentencia y emite sus instrucciones."""
        if self.match(TokenKind.RETURN):
            self.return_statement()
            return
        if self.match(TokenKind.IF):
            self.if_statement()
            return
        if self.match(TokenKind.WHILE):
            self.while_statement()
            return
        if self.match(TokenKind.FOR):
            self.for_statement()
            return
        if self.match(TokenKind.LEFT_BRACE):
            self.begin_scope()
            self.block()
            self.end_scope()
            return

        if self.match(TokenKind.PRINT):
            self.expression()
            self.consume(TokenKind.SEMICOLON, "Se esperaba ';' después de print")
            self.chunk.emit(OpCode.OP_PRINT, self.previous().line)
            return

        self.expression()
        self.consume(TokenKind.SEMICOLON, "Se esperaba ';' después de la expresión")
        self.chunk.emit(OpCode.OP_POP, self.previous().line)

    def return_statement(self) -> None:
        """Compila ``return (expresión)? ;``."""
        if not self.in_function:
            raise ParseError("No se puede usar 'return' fuera de una función")
        if self.match(TokenKind.SEMICOLON):
            self.chunk.emit(OpCode.OP_NIL, self.previous().line)
        else:
            self.expression()
            self.consume(TokenKind.SEMICOLON, "Se esperaba ';' después de return")
        self.chunk.emit(OpCode.OP_RETURN, self.previous().line)

    def block(self) -> None:
        """Lee el contenido de un bloque cuya llave de apertura ya se consumió."""
        while not self.is_at_end() and not self.check(TokenKind.RIGHT_BRACE):
            self.declaration()
        self.consume(TokenKind.RIGHT_BRACE, "Se esperaba '}' después del bloque")

    #  Expresiones

    def expression(self) -> None:
        """expression → assignment"""
        self.assignment()

    def _is_property_assignment_start(self) -> bool:
        """Indica si el token actual inicia una asignación a propiedad."""
        if self.is_at_end():
            return False
        first = self.peek()
        if first.kind not in (TokenKind.IDENTIFIER, TokenKind.THIS, TokenKind.SUPER):
            return False
        if self.current + 1 >= len(self.tokens):
            return False
        if self.tokens[self.current + 1].kind != TokenKind.DOT:
            return False
        if self.current + 2 >= len(self.tokens):
            return False
        if self.tokens[self.current + 2].kind != TokenKind.IDENTIFIER:
            return False
        if self.current + 3 >= len(self.tokens):
            return False
        return self.tokens[self.current + 3].kind == TokenKind.EQUAL

    def _compile_property_assignment(self) -> None:
        """Compila ``obj.prop = val`` o ``this.prop = val``."""
        # Compilar el objeto
        if self.match(TokenKind.THIS):
            self.chunk.emit(OpCode.OP_GET_LOCAL, self.previous().line, 0)
        elif self.match(TokenKind.SUPER):
            raise ParseError("No se puede asignar a una propiedad de super")
        else:
            name = self.advance()
            slot = self.resolve_local(name)
            if slot is not None:
                self.chunk.emit(OpCode.OP_GET_LOCAL, name.line, slot)
            else:
                upvalue_index = self.resolve_upvalue(name)
                if upvalue_index is not None:
                    self.chunk.emit(OpCode.OP_GET_UPVALUE, name.line, upvalue_index)
                else:
                    index = self.chunk.add_constant(name.lexeme)
                    self.chunk.emit(OpCode.OP_GET_GLOBAL, name.line, index)

        # Consumir .prop
        self.consume(TokenKind.DOT, "Se esperaba '.' después del objeto")
        prop_name = self.consume(TokenKind.IDENTIFIER, "Se esperaba un nombre de propiedad")
        self.consume(TokenKind.EQUAL, "Se esperaba '=' después del nombre")

        # Compilar el valor
        self.assignment()

        # Emitir OP_SET_PROPERTY
        index = self.chunk.add_constant(prop_name.lexeme)
        self.chunk.emit(OpCode.OP_SET_PROPERTY, prop_name.line, index)

    def assignment(self) -> None:
        """assignment → equality ( '=' assignment )?"""
        # Asignación a propiedad: obj.prop = val
        if self._is_property_assignment_start():
            self._compile_property_assignment()
            return

        # Asignación a variable: ident = val
        if self.check(TokenKind.IDENTIFIER) and self._peek_next() == TokenKind.EQUAL:
            name = self.advance()
            self.consume(TokenKind.EQUAL, "Se esperaba '=' después del nombre")
            self.assignment()
            slot = self.resolve_local(name)
            if slot is not None:
                self.chunk.emit(OpCode.OP_SET_LOCAL, name.line, slot)
            else:
                upvalue_index = self.resolve_upvalue(name)
                if upvalue_index is not None:
                    self.chunk.emit(OpCode.OP_SET_UPVALUE, name.line, upvalue_index)
                else:
                    index = self.chunk.add_constant(name.lexeme)
                    self.chunk.emit(OpCode.OP_SET_GLOBAL, name.line, index)
            return

        self.logical_or()
        if self.match(TokenKind.EQUAL):
            token = self.previous()
            raise ParseError(
                f"Destino inválido de asignación en la línea {token.line}, "
                f"columna {token.column}"
            )

    def logical_or(self) -> None:
        """logical_or → logical_and ( 'or' logical_and )*"""
        self.logical_and()
        while self.match(TokenKind.OR):
            else_jump = self.emit_jump(OpCode.OP_JUMP_IF_FALSE, self.previous().line)
            end_jump = self.emit_jump(OpCode.OP_JUMP, self.previous().line)
            self.patch_jump(else_jump)
            self.chunk.emit(OpCode.OP_POP, self.previous().line)
            self.logical_and()
            self.patch_jump(end_jump)

    def logical_and(self) -> None:
        """logical_and → equality ( 'and' equality )*"""
        self.equality()
        while self.match(TokenKind.AND):
            end_jump = self.emit_jump(OpCode.OP_JUMP_IF_FALSE, self.previous().line)
            self.chunk.emit(OpCode.OP_POP, self.previous().line)
            self.equality()
            self.patch_jump(end_jump)

    def equality(self) -> None:
        """equality → comparison ( ( '!=' | '==' ) comparison )*"""
        self.comparison()
        while self.match(TokenKind.BANG_EQUAL, TokenKind.EQUAL_EQUAL):
            operator = self.previous()
            self.comparison()
            if operator.kind == TokenKind.BANG_EQUAL:
                self.chunk.emit(OpCode.OP_EQUAL, operator.line)
                self.chunk.emit(OpCode.OP_NOT, operator.line)
            else:
                self.chunk.emit(OpCode.OP_EQUAL, operator.line)

    def comparison(self) -> None:
        """comparison → term ( ( '>' | '>=' | '<' | '<=' ) term )*"""
        self.term()
        while self.match(
            TokenKind.GREATER, TokenKind.GREATER_EQUAL,
            TokenKind.LESS, TokenKind.LESS_EQUAL,
        ):
            operator = self.previous()
            self.term()
            if operator.kind == TokenKind.GREATER:
                self.chunk.emit(OpCode.OP_GREATER, operator.line)
            elif operator.kind == TokenKind.GREATER_EQUAL:
                # a >= b  ⇔  !(a < b)
                self.chunk.emit(OpCode.OP_LESS, operator.line)
                self.chunk.emit(OpCode.OP_NOT, operator.line)
            elif operator.kind == TokenKind.LESS:
                self.chunk.emit(OpCode.OP_LESS, operator.line)
            else:  # LESS_EQUAL
                # a <= b  ⇔  !(a > b)
                self.chunk.emit(OpCode.OP_GREATER, operator.line)
                self.chunk.emit(OpCode.OP_NOT, operator.line)

    def term(self) -> None:
        """term → factor ( ( '-' | '+' ) factor )*"""
        self.factor()
        while self.match(TokenKind.MINUS, TokenKind.PLUS):
            operator = self.previous()
            self.factor()
            if operator.kind == TokenKind.MINUS:
                self.chunk.emit(OpCode.OP_SUBTRACT, operator.line)
            else:
                self.chunk.emit(OpCode.OP_ADD, operator.line)

    def factor(self) -> None:
        """factor → unary ( ( '/' | '*' | '%' ) unary )*"""
        self.unary()
        while self.match(TokenKind.SLASH, TokenKind.STAR, TokenKind.PERCENT):
            operator = self.previous()
            self.unary()
            if operator.kind == TokenKind.SLASH:
                self.chunk.emit(OpCode.OP_DIVIDE, operator.line)
            elif operator.kind == TokenKind.PERCENT:
                self.chunk.emit(OpCode.OP_MODULO, operator.line)
            else:
                self.chunk.emit(OpCode.OP_MULTIPLY, operator.line)

    def unary(self) -> None:
        """unary → ( '!' | '-' ) unary | primary"""
        if self.match(TokenKind.BANG, TokenKind.MINUS):
            operator = self.previous()
            self.unary()
            if operator.kind == TokenKind.BANG:
                self.chunk.emit(OpCode.OP_NOT, operator.line)
            else:
                self.chunk.emit(OpCode.OP_NEGATE, operator.line)
        else:
            self.primary()

    def primary(self) -> None:
        """primary → NUMBER | STRING | true | false | nil | '(' expression ')'"""
        if self.match(TokenKind.FALSE):
            self.chunk.emit(OpCode.OP_FALSE, self.previous().line)
            return
        if self.match(TokenKind.TRUE):
            self.chunk.emit(OpCode.OP_TRUE, self.previous().line)
            return
        if self.match(TokenKind.NIL):
            self.chunk.emit(OpCode.OP_NIL, self.previous().line)
            return
        if self.match(TokenKind.THIS):
            token = self.previous()
            self.chunk.emit(OpCode.OP_GET_LOCAL, token.line, 0)
            # Postfix: property access and calls
            while True:
                if self.match(TokenKind.DOT):
                    name = self.consume(TokenKind.IDENTIFIER, "Se esperaba un nombre de propiedad")
                    self.chunk.emit(OpCode.OP_GET_PROPERTY, name.line, self.chunk.add_constant(name.lexeme))
                elif self.match(TokenKind.LEFT_PAREN):
                    arg_count = 0
                    if not self.check(TokenKind.RIGHT_PAREN):
                        self.expression()
                        arg_count += 1
                        while self.match(TokenKind.COMMA):
                            self.expression()
                            arg_count += 1
                    self.consume(TokenKind.RIGHT_PAREN, "Se esperaba ')' después de los argumentos")
                    self.chunk.emit(OpCode.OP_CALL, self.previous().line, arg_count)
                else:
                    break
            return
        if self.match(TokenKind.SUPER):
            token = self.previous()
            self.consume(TokenKind.DOT, "Se esperaba '.' después de super")
            name = self.consume(TokenKind.IDENTIFIER, "Se esperaba un nombre de método")
            self.chunk.emit(OpCode.OP_GET_SUPER, token.line, self.chunk.add_constant(name.lexeme))
            # Postfix: calls
            while self.match(TokenKind.LEFT_PAREN):
                arg_count = 0
                if not self.check(TokenKind.RIGHT_PAREN):
                    self.expression()
                    arg_count += 1
                    while self.match(TokenKind.COMMA):
                        self.expression()
                        arg_count += 1
                self.consume(TokenKind.RIGHT_PAREN, "Se esperaba ')' después de los argumentos")
                self.chunk.emit(OpCode.OP_CALL, token.line, arg_count)
            return
        if self.match(TokenKind.NUMBER, TokenKind.STRING):
            token = self.previous()
            self.chunk.emit(
                OpCode.OP_CONSTANT, token.line, self.chunk.add_constant(token.literal)
            )
            return
        if self.match(TokenKind.IDENTIFIER):
            name = self.previous()
            slot = self.resolve_local(name)
            if slot is not None:
                self.chunk.emit(OpCode.OP_GET_LOCAL, name.line, slot)
            else:
                upvalue_index = self.resolve_upvalue(name)
                if upvalue_index is not None:
                    self.chunk.emit(OpCode.OP_GET_UPVALUE, name.line, upvalue_index)
                else:
                    index = self.chunk.add_constant(name.lexeme)
                    self.chunk.emit(OpCode.OP_GET_GLOBAL, name.line, index)

            # Llamadas y acceso a propiedades: f(x), obj.prop, f(x).prop
            while True:
                if self.match(TokenKind.DOT):
                    prop_name = self.consume(TokenKind.IDENTIFIER, "Se esperaba un nombre de propiedad")
                    self.chunk.emit(OpCode.OP_GET_PROPERTY, prop_name.line, self.chunk.add_constant(prop_name.lexeme))
                elif self.match(TokenKind.LEFT_PAREN):
                    arg_count = 0
                    if not self.check(TokenKind.RIGHT_PAREN):
                        self.expression()
                        arg_count += 1
                        while self.match(TokenKind.COMMA):
                            self.expression()
                            arg_count += 1
                    self.consume(TokenKind.RIGHT_PAREN, "Se esperaba ')' después de los argumentos")
                    self.chunk.emit(OpCode.OP_CALL, name.line, arg_count)
                else:
                    break
            return
        if self.match(TokenKind.LEFT_PAREN):
            self.expression()
            if not self.match(TokenKind.RIGHT_PAREN):
                token = self.peek()
                raise ParseError(
                    f"Se esperaba ')' después de la expresión, "
                    f"se encontró {token.lexeme!r} en la línea {token.line}, "
                    f"columna {token.column}"
                )
            return

        token = self.peek()
        raise ParseError(
            f"Se esperaba una expresión, se encontró {token.lexeme!r} "
            f"en la línea {token.line}, columna {token.column}"
        )

    # ---------- Saltos ---------- #

    def emit_jump(self, opcode: OpCode, line: int) -> int:
        """Emite un salto con placeholder de 2 bytes. Devuelve la posición del primer byte del operando."""
        self.chunk.write_byte(opcode.value, line)
        self.chunk.write_byte(0xFF, line)
        self.chunk.write_byte(0xFF, line)
        return len(self.chunk) - 2

    def patch_jump(self, offset: int) -> None:
        """Emparcha un salto con el offset calculado desde la posición actual."""
        target = len(self.chunk) - offset - 2
        self.chunk.patch(offset, (target >> 8) & 0xFF)
        self.chunk.patch(offset + 1, target & 0xFF)

    def emit_loop(self, loop_start: int, line: int) -> None:
        """Emite un salto hacia atrás hacia loop_start."""
        self.chunk.write_byte(OpCode.OP_LOOP.value, line)
        target = len(self.chunk) - loop_start + 2
        self.chunk.write_byte((target >> 8) & 0xFF, line)
        self.chunk.write_byte(target & 0xFF, line)

    # ---------- Tokens ---------- #

    def is_at_end(self) -> bool:
        """Indica si el cursor llegó al token EOF."""
        return self.peek().kind == TokenKind.EOF

    def peek(self) -> Token:
        """Devuelve el token actual sin consumirlo."""
        return self.tokens[self.current]

    def _peek_next(self) -> TokenKind:
        """Devuelve el tipo del token siguiente al actual, sin consumirlo."""
        if self.current + 1 < len(self.tokens):
            return self.tokens[self.current + 1].kind
        return TokenKind.EOF

    def previous(self) -> Token:
        """Devuelve el último token consumido."""
        return self.tokens[self.current - 1]

    def advance(self) -> Token:
        """Consume el token actual y lo devuelve."""
        if not self.is_at_end():
            self.current += 1
        return self.previous()

    def match(self, *kinds: TokenKind) -> bool:
        """Consume el token actual si es alguno de los tipos pedidos."""
        for kind in kinds:
            if self.check(kind):
                self.advance()
                return True
        return False

    def check(self, kind: TokenKind) -> bool:
        """Indica si el token actual es del tipo pedido."""
        if self.is_at_end():
            return False
        return self.peek().kind == kind

    def consume(self, kind: TokenKind, message: str) -> Token:
        """Exige un tipo de token y lo consume, o informa un error de sintaxis."""
        if not self.check(kind):
            token = self.peek()
            raise ParseError(
                f"{message}, se encontró {token.lexeme!r} "
                f"en la línea {token.line}, columna {token.column}"
            )
        return self.advance()
