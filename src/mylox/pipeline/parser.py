"""Construcción del AST de un programa de Lox por descenso recursivo.

Las reglas consumen tokens y devuelven nodos; todavía no calculan valores
ni ejecutan sentencias. Los errores de estructura se informan con ParseError.
"""

from __future__ import annotations

from ..errors import ParseError
from ..nodes import (
    Assign, Binary, BlockStmt, ExprStmt, Grouping, IfStmt, Literal, Node,
    PrintStmt, Unary, VarDecl, Variable, WhileStmt,
)
from ..tokens import Token, TokenKind


class Parser:
    """Convierte una lista de tokens terminada en EOF en un programa AST.

    ``current`` señala el próximo token por consumir. Cada método de una
    regla llama a otras reglas para construir sus componentes, respetando
    la precedencia de expresiones y la estructura de declaraciones y cuerpos.
    """

    def __init__(self, tokens: list[Token]):
        """Conserva la secuencia producida por el lexer e inicia su cursor.

        ``tokens`` debe incluir EOF como último token. El parser recorre
        la lista mediante ``current`` sin modificar los objetos Token.
        """
        self.tokens = tokens
        self.current = 0

    def parse(self) -> list[Node]:
        """Construye la lista completa de declaraciones y sentencias hasta EOF.

        Cada vuelta agrega un nodo producido por ``_declaration()``. Un
        programa vacío devuelve una lista vacía. Cualquier error de sintaxis
        se propaga como ParseError, incluso después de una sentencia válida;
        el parser no ejecuta el programa ni devuelve una lista parcial.
        """
        statements: list[Node] = []
        while not self._check(TokenKind.EOF):
            statements.append(self._declaration())
        return statements

    def _declaration(self) -> Node:
        """Lee una declaración ``var`` o delega en una sentencia ordinaria.

        La declaración tiene forma ``var nombre (= expresión)? ;``. Guarda
        un inicializador opcional en VarDecl; su ausencia se representa con
        None en el AST. Aquí se reconoce la sintaxis: el nombre y su valor
        se incorporan al ambiente recién al ejecutar el nodo.
        """
        if self._match(TokenKind.VAR):
            name = self._consume(TokenKind.IDENTIFIER, "Se esperaba un nombre de variable")
            initializer = self._expression() if self._match(TokenKind.EQUAL) else None
            self._consume(TokenKind.SEMICOLON, "Se esperaba ';' después de var")
            return VarDecl(name, initializer)
        return self._statement()

    def _statement(self) -> Node:
        """Selecciona la forma de sentencia a partir del próximo token.

        Reconoce if, while, for, print y bloques. Si ninguna palabra o llave
        inicia esas formas, construye una ExprStmt. PrintStmt y ExprStmt
        necesitan un ``;`` final. Los cuerpos de control también llaman
        a este método, lo que permite anidar sentencias recursivamente.
        """
        if self._match(TokenKind.IF):
            return self._if_statement()
        if self._match(TokenKind.WHILE):
            return self._while_statement()
        if self._match(TokenKind.FOR):
            return self._for_statement()
        if self._match(TokenKind.PRINT):
            expression = self._expression()
            self._consume(TokenKind.SEMICOLON, "Se esperaba ';' después de print")
            return PrintStmt(expression)
        if self._match(TokenKind.LEFT_BRACE):
            return BlockStmt(self._block())
        expression = self._expression()
        self._consume(TokenKind.SEMICOLON, "Se esperaba ';' después de la expresión")
        return ExprStmt(expression)

    def _block(self) -> list[Node]:
        """Lee el contenido de un bloque cuya llave de apertura ya se consumió.

        Reúne declaraciones y sentencias hasta ``}``, consume esa llave y
        devuelve la lista del cuerpo. Si llega a EOF antes del cierre,
        ``_consume()`` informa ParseError. No crea un ambiente: ese efecto
        corresponde a la ejecución de BlockStmt en el intérprete.
        """
        statements: list[Node] = []
        while not self._check(TokenKind.RIGHT_BRACE) and not self._check(TokenKind.EOF):
            statements.append(self._declaration())
        self._consume(TokenKind.RIGHT_BRACE, "Se esperaba '}' después del bloque")
        return statements

    def _if_statement(self) -> Node:
        """Construye IfStmt después de haber consumido la palabra ``if``.

        Exige una expresión entre paréntesis, lee una sentencia para la rama
        verdadera y una rama opcional después de ``else``. La llamada recursiva
        a ``_statement()`` hace que un else pertenezca al if pendiente más
        cercano. Ambas ramas quedan en el AST sin ejecutarse durante el parseo.
        """
        self._consume(TokenKind.LEFT_PAREN, "Se esperaba '(' después de if")
        condition = self._expression()
        self._consume(TokenKind.RIGHT_PAREN, "Se esperaba ')' después de if")
        then_branch = self._statement()
        else_branch = self._statement() if self._match(TokenKind.ELSE) else None
        return IfStmt(condition, then_branch, else_branch)

    def _while_statement(self) -> Node:
        """Construye WhileStmt a partir de una condición y una sentencia cuerpo.

        La palabra ``while`` ya fue consumida. Exige paréntesis alrededor
        de la condición y conserva el nodo de esa expresión para que el
        intérprete pueda reevaluarlo antes de cada vuelta del bucle.
        """
        self._consume(TokenKind.LEFT_PAREN, "Se esperaba '(' después de while")
        condition = self._expression()
        self._consume(TokenKind.RIGHT_PAREN, "Se esperaba ')' después de while")
        return WhileStmt(condition, self._statement())

    def _for_statement(self) -> Node:
        """Lee el encabezado y cuerpo de for y los transforma en bloque y while.

        El inicializador opcional puede ser una declaración var o una sentencia
        de expresión. La condición ausente se convierte en Literal(True).
        Si hay incremento, lo agrega como ExprStmt después del cuerpo en un
        BlockStmt. Finalmente envuelve el WhileStmt con el inicializador,
        si existe, en otro bloque para limitar el ámbito de sus variables.
        Devuelve esos nodos comunes; el AST no necesita una clase ForStmt.
        """
        self._consume(TokenKind.LEFT_PAREN, "Se esperaba '(' después de for")
        if self._match(TokenKind.SEMICOLON):
            initializer = None
        elif self._match(TokenKind.VAR):
            name = self._consume(TokenKind.IDENTIFIER, "Se esperaba un nombre de variable")
            value = self._expression() if self._match(TokenKind.EQUAL) else None
            self._consume(TokenKind.SEMICOLON, "Se esperaba ';' después de var")
            initializer = VarDecl(name, value)
        else:
            value = self._expression()
            self._consume(TokenKind.SEMICOLON, "Se esperaba ';' después del inicio de for")
            initializer = ExprStmt(value)

        condition = Literal(True) if self._check(TokenKind.SEMICOLON) else self._expression()
        self._consume(TokenKind.SEMICOLON, "Se esperaba ';' después de la condición")
        increment = None if self._check(TokenKind.RIGHT_PAREN) else self._expression()
        self._consume(TokenKind.RIGHT_PAREN, "Se esperaba ')' después de for")

        body = self._statement()
        if increment is not None:
            body = BlockStmt([body, ExprStmt(increment)])
        loop: Node = WhileStmt(condition, body)
        if initializer is not None:
            loop = BlockStmt([initializer, loop])
        return loop

    # Reglas de producción 

    def _expression(self) -> Node:
        """Inicia una expresión por la regla de menor precedencia: assignment.

        Devuelve el nodo de la expresión sin consumir su terminador externo,
        como ``;``, ``)`` o ``,``. La regla que la contiene exige ese token.
        """

        return self._assignment()

    def _assignment(self) -> Node:
        """Construye una asignación o devuelve la expresión sin asignación.

        Primero lee igualdad; si aparece ``=``, lee recursivamente la derecha.
        Así ``a = b = 3`` se agrupa como ``a = (b = 3)``. El destino debe ser
        un nodo Variable: cualquier otra forma produce ParseError en el ``=``.
        Devuelve Assign sin consultar ni modificar los ambientes de ejecución.
        """
        expression = self._equality()
        if self._match(TokenKind.EQUAL):
            equals = self._previous()
            value = self._assignment()
            if isinstance(expression, Variable):
                return Assign(expression.name, value)
            raise ParseError(
                f"Destino inválido de asignación en la línea {equals.line}, "
                f"columna {equals.column}"
            )
        return expression

    def _equality(self) -> Node:
        """Lee ``comparison ((!= | ==) comparison)*`` y devuelve su AST.

        Cada operando se construye con la regla de comparación, que tiene
        mayor precedencia. El ciclo incorpora las igualdades de izquierda
        a derecha en nodos Binary, sin comparar todavía sus valores.
        """

        expression = self._comparison()

        while self._match(TokenKind.BANG_EQUAL, TokenKind.EQUAL_EQUAL):
            operator = self._previous()
            right = self._comparison()
            expression = Binary(expression, operator, right)

        return expression

    def _comparison(self) -> Node:
        """Lee ``term ((> | >= | < | <=) term)*`` y construye nodos Binary.

        ``_term()`` arma completamente las sumas y restas de cada operando
        antes de incorporarlas a una comparación. Las comparaciones sucesivas
        se agrupan de izquierda a derecha por el ciclo.
        """

        expression = self._term()

        while self._match(
            TokenKind.GREATER,
            TokenKind.GREATER_EQUAL,
            TokenKind.LESS,
            TokenKind.LESS_EQUAL,
        ):
            operator = self._previous()
            right = self._term()
            expression = Binary(expression, operator, right)

        return expression

    def _term(self) -> Node:
        """Lee ``factor ((- | +) factor)*`` para construir sumas y restas.

        Obtener cada operando con ``_factor()`` da mayor precedencia a
        multiplicaciones y divisiones. El árbol acumulado queda a la izquierda,
        por lo que ``5 - 3 - 1`` representa ``(5 - 3) - 1``.
        """

        expression = self._factor()

        while self._match(TokenKind.MINUS, TokenKind.PLUS):
            operator = self._previous()
            right = self._factor()
            expression = Binary(expression, operator, right)

        return expression

    def _factor(self) -> Node:
        """Lee ``unary ((/ | *) unary)*`` para construir productos y divisiones.

        La regla unaria produce cada operando antes de agregarlo al Binary.
        El ciclo agrupa operadores de este nivel de izquierda a derecha
        y devuelve el árbol completo a la regla de suma o resta.
        """

        expression = self._unary()

        while self._match(TokenKind.SLASH, TokenKind.STAR):
            operator = self._previous()
            right = self._unary()
            expression = Binary(expression, operator, right)

        return expression

    def _unary(self) -> Node:
        """Lee un prefijo ``!`` o ``-``, o delega en una expresión primaria.

        La llamada recursiva permite prefijos encadenados: ``!-1`` se
        representa como Unary(!, Unary(-, Literal(1))). Estos nodos quedan
        dentro de los operandos de las reglas de mayor extensión.
        """

        if self._match(TokenKind.BANG, TokenKind.MINUS):
            operator = self._previous()
            right = self._unary()
            return Unary(operator, right)

        return self._primary()

    def _primary(self) -> Node:
        """Construye un literal, una referencia a variable o una agrupación.

        NUMBER y STRING usan el valor del token; true, false y nil se convierten
        en Literal con True, False y None. IDENTIFIER se convierte en Variable.
        Con ``(`` lee una expresión completa y exige ``)`` para crear Grouping.
        Si el token no puede iniciar ninguna de estas formas, lanza ParseError.
        """

        if self._match(TokenKind.FALSE):
            return Literal(False)

        if self._match(TokenKind.TRUE):
            return Literal(True)

        if self._match(TokenKind.NIL):
            return Literal(None)

        if self._match(TokenKind.NUMBER, TokenKind.STRING):
            return Literal(self._previous().literal)

        if self._match(TokenKind.IDENTIFIER):
            return Variable(self._previous())

        if self._match(TokenKind.LEFT_PAREN):
            expression = self._expression()

            if not self._match(TokenKind.RIGHT_PAREN):
                token = self._peek()
                raise ParseError(
                    f"Se esperaba ')' después de la expresión, "
                    f"se encontró {token.lexeme!r} "
                    f"en la línea {token.line}, columna {token.column}"
                )

            return Grouping(expression)

        token = self._peek()
        raise ParseError(
            f"Se esperaba una expresión, "
            f"se encontró {token.lexeme!r} "
            f"en la línea {token.line}, columna {token.column}"
        )

    # Helpers 

    def _peek(self) -> Token:
        """Devuelve el token señalado por el cursor sin avanzar.

        Permite mirar la próxima pieza para elegir una regla o exigir un
        delimitador. También puede devolver el token EOF de la lista.
        """

        return self.tokens[self.current]

    def _previous(self) -> Token:
        """Devuelve el token ubicado inmediatamente antes del cursor.

        Se llama después de consumir un token, por ejemplo para conservar
        el operador de un nodo o el nombre de una variable.
        """

        return self.tokens[self.current - 1]

    def _advance(self) -> Token:
        """Devuelve el token actual y avanza el cursor si no es EOF.

        Mantener el cursor en EOF permite que las comprobaciones posteriores
        sigan observando el fin de la fuente sin salir de la lista de tokens.
        """

        token = self._peek()

        if token.kind is not TokenKind.EOF:
            self.current += 1

        return token

    def _match(self, *kinds: TokenKind) -> bool:
        """Consume el token si su tipo coincide con alguno de los recibidos.

        Devuelve True al encontrar una coincidencia. Si no coincide con
        ninguno, devuelve False y conserva el cursor en su posición.
        """

        for kind in kinds:
            if self._check(kind):
                self._advance()
                return True

        return False

    def _check(self, kind: TokenKind) -> bool:
        """Indica si el próximo token tiene el tipo solicitado, sin consumirlo.

        A diferencia de ``_match()``, esta mirada anticipada nunca avanza
        el cursor; se usa también para detectar cierres de bloque y EOF.
        """

        return self._peek().kind is kind

    def _consume(self, kind: TokenKind, message: str) -> Token:
        """Exige un tipo de token y lo consume, o informa un error de sintaxis.

        Si coincide, devuelve el Token y avanza. Si no coincide, lanza
        ParseError con ``message``, el lexema encontrado y su línea y columna.
        El llamador usa este método para nombres y delimitadores obligatorios.
        """
        if self._check(kind):
            return self._advance()
        token = self._peek()
        raise ParseError(
            f"{message}, se encontró {token.lexeme!r} "
            f"en la línea {token.line}, columna {token.column}"
        )
