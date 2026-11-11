"""Compilador de Lox a bytecode, de una sola pasada"""
from __future__ import annotations

from ..errors import CompileError, ParseError
from ..tokens import Token, TokenKind
from .chunk import Chunk
from .function import Function
from .opcodes import OpCode


class Local:
    """Un slot local y su ámbito; las capturas se cierran al salir del bloque."""

    def __init__(self, name: str, depth: int) -> None:
        self.name = name
        self.depth = depth
        self.is_captured = False


class Compiler:
    """Traduce una secuencia de tokens en un chunk de bytecode. No construye AST: parsea y emite instrucciones en el mismo recorrido
    """

    def __init__(self, tokens: list[Token], start: int = 0, enclosing: Compiler | None = None) -> None:
        """Conserva la secuencia de tokens e inicia el cursor y el chunk."""
        self.tokens = tokens
        self.current = start
        self.chunk = Chunk()
        self.scope_depth = 0
        self.locals: list[Local] = []
        self.in_function = False
        self.class_has_superclass = enclosing.class_has_superclass if enclosing else None
        self.enclosing = enclosing
        self.upvalues: list[tuple[bool, int]] = []

    # ---------- Scopes ---------- #

    def begin_scope(self) -> None:
        """Entra a un bloque nuevo, incrementando la profundidad de scope."""
        self.scope_depth += 1

    def end_scope(self) -> None:
        """Sale del bloque actual y retira las variables locales del stack."""
        self.scope_depth -= 1
        while self.locals and self.locals[-1].depth > self.scope_depth:
            local = self.locals.pop()
            if local.is_captured:
                self.chunk.emit(OpCode.OP_CLOSE_UPVALUE, self.previous().line)
            else:
                self.chunk.emit(OpCode.OP_POP, self.previous().line)

    def declare(self, name: str) -> None:
        """Registra una variable local en el scope actual."""
        if len(self.locals) >= 256:
            raise CompileError("Un ámbito de función admite hasta 256 slots", self.previous())
        self.locals.append(Local(name, self.scope_depth))

    def current_local(self, name: str) -> int | None:
        for slot in range(len(self.locals) - 1, -1, -1):
            local = self.locals[slot]
            if local.depth < self.scope_depth:
                break
            if local.name == name:
                return slot
        return None

    def define(self, name: Token) -> None:
        if self.scope_depth == 0:
            self.chunk.emit(OpCode.OP_DEFINE_GLOBAL, name.line, self.chunk.add_constant(name.lexeme))
        elif (slot := self.current_local(name.lexeme)) is not None:
            self.chunk.emit(OpCode.OP_SET_LOCAL, name.line, slot)
            self.chunk.emit(OpCode.OP_POP, name.line)
        else:
            self.declare(name.lexeme)

    def resolve_local(self, name: Token) -> int | None:
        """Devuelve el slot de la variable local, o None si es global."""
        for idx, local in enumerate(reversed(self.locals), 1):
            if local.name == name.lexeme:
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
        if self.match(TokenKind.EQUAL):
            self.expression()
        else:
            self.chunk.emit(OpCode.OP_NIL, name.line)

        self.consume(TokenKind.SEMICOLON, "Se esperaba ';' después de var")

        self.define(name)

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
        name = self.consume(TokenKind.IDENTIFIER, "Se esperaba un nombre de función")
        new_local = self.scope_depth > 0 and self.current_local(name.lexeme) is None
        if new_local:
            self.declare(name.lexeme)
        self.function_body(name)
        if not new_local:
            self.define(name)

    def function_body(self, name: Token, method: bool = False) -> None:
        self.consume(TokenKind.LEFT_PAREN, "Se esperaba '(' después del nombre")
        body = Compiler(self.tokens, start=self.current, enclosing=self)
        body.in_function = True
        body.begin_scope()
        body.declare("this" if method else "")

        arity = 0
        if not self.check(TokenKind.RIGHT_PAREN):
            while True:
                param = self.consume(TokenKind.IDENTIFIER, "Se esperaba un parámetro")
                arity += 1
                if arity > 255:
                    raise CompileError("Una función admite hasta 255 parámetros", param)
                body.declare(param.lexeme)
                if not self.match(TokenKind.COMMA):
                    break
        self.consume(TokenKind.RIGHT_PAREN, "Se esperaba ')' después de los parámetros")
        self.consume(TokenKind.LEFT_BRACE, "Se esperaba '{' antes del cuerpo")
        body.current = self.current
        body.block()
        body.chunk.emit(OpCode.OP_NIL, body.previous().line)
        body.chunk.emit(OpCode.OP_RETURN, body.previous().line)
        self.current = body.current

        function = Function(name.lexeme)
        function.chunk = body.chunk
        function.arity = arity
        function.upvalue_count = len(body.upvalues)
        function.is_initializer = method and name.lexeme == "init"
        self.chunk.emit(OpCode.OP_CLOSURE, name.line, self.chunk.add_constant(function))
        for is_local, slot in body.upvalues:
            self.chunk.write_byte(int(is_local), name.line)
            self.chunk.write_byte(slot, name.line)

    def class_declaration(self) -> None:
        name = self.consume(TokenKind.IDENTIFIER, "Se esperaba un nombre de clase")
        self.chunk.emit(OpCode.OP_CLASS, name.line, self.chunk.add_constant(name.lexeme))
        self.define(name)

        previous_class = self.class_has_superclass
        self.class_has_superclass = self.match(TokenKind.LESS)
        if self.class_has_superclass:
            superclass = self.consume(TokenKind.IDENTIFIER, "Se esperaba nombre de superclase")
            if superclass.lexeme == name.lexeme:
                raise CompileError("Una clase no puede heredarse a sí misma", superclass)
            self.variable(superclass)
            self.begin_scope()
            self.declare("super")
            self.variable(name)
            self.chunk.emit(OpCode.OP_INHERIT, name.line)

        self.variable(name)
        self.consume(TokenKind.LEFT_BRACE, "Se esperaba '{' después del nombre")
        while not self.check(TokenKind.RIGHT_BRACE) and not self.is_at_end():
            method = self.consume(TokenKind.IDENTIFIER, "Se esperaba un nombre de método")
            self.function_body(method, method=True)
            self.chunk.emit(OpCode.OP_METHOD, method.line, self.chunk.add_constant(method.lexeme))
        self.consume(TokenKind.RIGHT_BRACE, "Se esperaba '}' después de la clase")
        self.chunk.emit(OpCode.OP_POP, name.line)
        if self.class_has_superclass:
            self.end_scope()
        self.class_has_superclass = previous_class

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

    def variable(self, name: Token, can_assign: bool = False) -> None:
        slot = self.resolve_local(name)
        if slot is not None:
            read, write = OpCode.OP_GET_LOCAL, OpCode.OP_SET_LOCAL
        else:
            slot = self.resolve_upvalue(name)
            if slot is not None:
                read, write = OpCode.OP_GET_UPVALUE, OpCode.OP_SET_UPVALUE
            else:
                slot = self.chunk.add_constant(name.lexeme)
                read, write = OpCode.OP_GET_GLOBAL, OpCode.OP_SET_GLOBAL
        if can_assign and self.match(TokenKind.EQUAL):
            self.assignment()
            self.chunk.emit(write, name.line, slot)
        else:
            self.chunk.emit(read, name.line, slot)

    def assignment(self) -> None:
        self.logical_or(can_assign=True)
        if self.match(TokenKind.EQUAL):
            raise CompileError("Destino inválido de asignación", self.previous())

    def logical_or(self, can_assign: bool = False) -> None:
        """logical_or → logical_and ( 'or' logical_and )*"""
        self.logical_and(can_assign)
        while self.match(TokenKind.OR):
            else_jump = self.emit_jump(OpCode.OP_JUMP_IF_FALSE, self.previous().line)
            end_jump = self.emit_jump(OpCode.OP_JUMP, self.previous().line)
            self.patch_jump(else_jump)
            self.chunk.emit(OpCode.OP_POP, self.previous().line)
            self.logical_and()
            self.patch_jump(end_jump)

    def logical_and(self, can_assign: bool = False) -> None:
        """logical_and → equality ( 'and' equality )*"""
        self.equality(can_assign)
        while self.match(TokenKind.AND):
            end_jump = self.emit_jump(OpCode.OP_JUMP_IF_FALSE, self.previous().line)
            self.chunk.emit(OpCode.OP_POP, self.previous().line)
            self.equality()
            self.patch_jump(end_jump)

    def equality(self, can_assign: bool = False) -> None:
        """equality → comparison ( ( '!=' | '==' ) comparison )*"""
        self.comparison(can_assign)
        while self.match(TokenKind.BANG_EQUAL, TokenKind.EQUAL_EQUAL):
            operator = self.previous()
            self.comparison()
            if operator.kind == TokenKind.BANG_EQUAL:
                self.chunk.emit(OpCode.OP_EQUAL, operator.line)
                self.chunk.emit(OpCode.OP_NOT, operator.line)
            else:
                self.chunk.emit(OpCode.OP_EQUAL, operator.line)

    def comparison(self, can_assign: bool = False) -> None:
        """comparison → term ( ( '>' | '>=' | '<' | '<=' ) term )*"""
        self.term(can_assign)
        while self.match(
            TokenKind.GREATER, TokenKind.GREATER_EQUAL,
            TokenKind.LESS, TokenKind.LESS_EQUAL,
        ):
            operator = self.previous()
            self.term()
            if operator.kind == TokenKind.GREATER:
                self.chunk.emit(OpCode.OP_GREATER, operator.line)
            elif operator.kind == TokenKind.GREATER_EQUAL:
                self.chunk.emit(OpCode.OP_GREATER_EQUAL, operator.line)
            elif operator.kind == TokenKind.LESS:
                self.chunk.emit(OpCode.OP_LESS, operator.line)
            else:
                self.chunk.emit(OpCode.OP_LESS_EQUAL, operator.line)

    def term(self, can_assign: bool = False) -> None:
        """term → factor ( ( '-' | '+' ) factor )*"""
        self.factor(can_assign)
        while self.match(TokenKind.MINUS, TokenKind.PLUS):
            operator = self.previous()
            self.factor()
            if operator.kind == TokenKind.MINUS:
                self.chunk.emit(OpCode.OP_SUBTRACT, operator.line)
            else:
                self.chunk.emit(OpCode.OP_ADD, operator.line)

    def factor(self, can_assign: bool = False) -> None:
        """factor → unary ( ( '/' | '*' | '%' ) unary )*"""
        self.unary(can_assign)
        while self.match(TokenKind.SLASH, TokenKind.STAR, TokenKind.PERCENT):
            operator = self.previous()
            self.unary()
            if operator.kind == TokenKind.SLASH:
                self.chunk.emit(OpCode.OP_DIVIDE, operator.line)
            elif operator.kind == TokenKind.PERCENT:
                self.chunk.emit(OpCode.OP_MODULO, operator.line)
            else:
                self.chunk.emit(OpCode.OP_MULTIPLY, operator.line)

    def unary(self, can_assign: bool = False) -> None:
        """unary → ( '!' | '-' ) unary | primary"""
        if self.match(TokenKind.BANG, TokenKind.MINUS):
            operator = self.previous()
            self.unary()
            if operator.kind == TokenKind.BANG:
                self.chunk.emit(OpCode.OP_NOT, operator.line)
            else:
                self.chunk.emit(OpCode.OP_NEGATE, operator.line)
        else:
            self.postfix(can_assign)

    def postfix(self, can_assign: bool) -> None:
        self.primary(can_assign)
        while True:
            if self.match(TokenKind.LEFT_PAREN):
                paren = self.previous()
                count = self.expression_list(TokenKind.RIGHT_PAREN)
                if count > 255:
                    raise CompileError("Una llamada admite hasta 255 argumentos", paren)
                self.chunk.emit(OpCode.OP_CALL, paren.line, count)
            elif self.match(TokenKind.DOT):
                name = self.consume(TokenKind.IDENTIFIER, "Se esperaba un nombre de propiedad")
                index = self.chunk.add_constant(name.lexeme)
                if can_assign and self.match(TokenKind.EQUAL):
                    self.assignment()
                    self.chunk.emit(OpCode.OP_SET_PROPERTY, name.line, index)
                else:
                    self.chunk.emit(OpCode.OP_GET_PROPERTY, name.line, index)
            elif self.match(TokenKind.LEFT_BRACKET):
                bracket = self.previous()
                self.expression()
                self.consume(TokenKind.RIGHT_BRACKET, "Se esperaba ']' después del índice")
                if can_assign and self.match(TokenKind.EQUAL):
                    self.assignment()
                    self.chunk.emit(OpCode.OP_SET_INDEX, bracket.line)
                else:
                    self.chunk.emit(OpCode.OP_GET_INDEX, bracket.line)
            else:
                break

    def expression_list(self, closing: TokenKind) -> int:
        count = 0
        if not self.check(closing):
            while True:
                self.expression()
                count += 1
                if not self.match(TokenKind.COMMA):
                    break
        self.consume(closing, "Se esperaba el cierre de la lista de expresiones")
        return count

    def primary(self, can_assign: bool) -> None:
        if self.match(TokenKind.FALSE):
            self.chunk.emit(OpCode.OP_FALSE, self.previous().line)
        elif self.match(TokenKind.TRUE):
            self.chunk.emit(OpCode.OP_TRUE, self.previous().line)
        elif self.match(TokenKind.NIL):
            self.chunk.emit(OpCode.OP_NIL, self.previous().line)
        elif self.match(TokenKind.THIS):
            token = self.previous()
            if self.class_has_superclass is None:
                raise CompileError("No se puede usar 'this' fuera de una clase", token)
            self.variable(token)
        elif self.match(TokenKind.SUPER):
            token = self.previous()
            if not self.class_has_superclass:
                raise CompileError("No se puede usar 'super' sin superclase", token)
            self.consume(TokenKind.DOT, "Se esperaba '.' después de super")
            name = self.consume(TokenKind.IDENTIFIER, "Se esperaba un nombre de método")
            self.variable(Token(TokenKind.THIS, "this", line=token.line, column=token.column))
            self.variable(token)
            self.chunk.emit(OpCode.OP_GET_SUPER, token.line, self.chunk.add_constant(name.lexeme))
        elif self.match(TokenKind.NUMBER, TokenKind.STRING):
            token = self.previous()
            self.chunk.emit(OpCode.OP_CONSTANT, token.line, self.chunk.add_constant(token.literal))
        elif self.match(TokenKind.IDENTIFIER):
            self.variable(self.previous(), can_assign)
        elif self.match(TokenKind.LEFT_PAREN):
            self.expression()
            self.consume(TokenKind.RIGHT_PAREN, "Se esperaba ')' después de la expresión")
        elif self.match(TokenKind.LEFT_BRACKET):
            bracket = self.previous()
            count = self.expression_list(TokenKind.RIGHT_BRACKET)
            if count > 255:
                raise CompileError("Un literal de lista admite hasta 255 elementos", bracket)
            self.chunk.emit(OpCode.OP_LIST, bracket.line, count)
        else:
            token = self.peek()
            raise ParseError(f"Se esperaba una expresión en la línea {token.line}, columna {token.column}")

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
