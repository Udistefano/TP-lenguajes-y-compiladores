# STATEMENTS: SENTENCIAS Y PROGRAMAS COMPLETOS

## 1. ¿Qué diferencia hay entre una expresión y una sentencia?

Una **expresión** produce un valor. Por ejemplo, `2 + 3` produce el número `5`.
Una **sentencia** indica una acción que el programa debe ejecutar. Puede usar una expresión para realizar esa acción.

Considerá este programa:

```lox
2 + 3;
print 2 + 3;
```

Las dos líneas calculan `5`, pero solamente la segunda lo escribe en la salida:

```text
5
```

La primera es una **sentencia de expresión**: evalúa `2 + 3` y descarta el resultado.
La segunda es una **sentencia print**: evalúa `2 + 3` y muestra el resultado.

El `;` marca el final de estas sentencias. No es parte de la suma: sirve para que el parser sepa dónde termina la instrucción.

## 2. ¿Qué hace el lexer con un programa de varias sentencias?

El [lexer](../src/mylox/pipeline/lexer.py) recibe todo el texto y entrega una lista de tokens:

```text
NUMBER(2) PLUS NUMBER(3) SEMICOLON
PRINT NUMBER(2) PLUS NUMBER(3) SEMICOLON
EOF
```

Los saltos de línea no separan instrucciones por sí solos. El lexer consume espacios y saltos de línea, pero conserva los `;` como tokens `SEMICOLON`.

También reconoce `print` como una palabra reservada y produce `PRINT`, en lugar de `IDENTIFIER`.
En esta etapa todavía no se calcula ni se imprime nada.

## 3. ¿Cómo cambió Parser.parse()?

Antes, `parse()` devolvía una sola expresión. Ahora el [parser](../src/mylox/pipeline/parser.py) devuelve una **lista de nodos** que representa el programa completo:

```python
statements = []
while not self._check(TokenKind.EOF):
    statements.append(self._declaration())
return statements
```

Cada vuelta lee una declaración o una sentencia completa y la agrega a la lista. El recorrido termina cuando encuentra `EOF`.

Esto tiene dos consecuencias:

- Un programa vacío es válido y produce una lista vacía.
- Un error después de la primera sentencia también se detecta. El parser debe revisar todo el programa.

Por ejemplo, `print 1; print 2 +;` produce un error de parseo en la segunda sentencia.
La CLI construye todo el AST antes de ejecutarlo, por lo que tampoco llega a imprimir el `1` de ese archivo.

`_declaration()` reconoce declaraciones como `var` y, para las demás formas, llama a `_statement()`.
Por ahora, las declaraciones de variables se explican en [variables.md](variables.md).

## 4. ¿Cómo reconoce una sentencia de expresión o print?

Las reglas se pueden resumir así:

```text
sentencia de expresión → expresión ";"
sentencia print       → "print" expresión ";"
```

En `_statement()`, el parser comprueba si el próximo token es `PRINT`.
Si lo es, consume la palabra, construye la expresión y exige el `;` final mediante `_consume()`.

Si no encontró una de las otras formas de sentencia, intenta construir una sentencia de expresión.
También exige su `;`.

Para el ejemplo inicial, el AST queda así. Los números y operadores están abreviados para que se vea la estructura:

```text
Programa: lista de nodos
├── ExprStmt
│   └── Binary(2, +, 3)
└── PrintStmt
    └── Binary(2, +, 3)
```

En [nodes.py](../src/mylox/nodes.py), ambos nodos guardan un campo `expression`.
La diferencia está en el tipo de nodo: ese tipo indica qué acción debe realizar el visitante.

## 5. ¿Cómo las ejecuta el intérprete?

`Interpreter.interpret()` recibe la lista y la recorre en orden:

```python
for statement in statements:
    statement.accept(self)
```

La ejecución mantiene nuestro **Visitor con double dispatch**:

```text
ExprStmt.accept(interpreter)
    → Interpreter.visit_expr_stmt(...)
    → evalúa la expresión y descarta el valor

PrintStmt.accept(interpreter)
    → Interpreter.visit_print_stmt(...)
    → evalúa la expresión, convierte el valor a texto y lo imprime
```

El tipo de nodo selecciona el método `visit_...`; el visitante concreto define qué hacer con ese nodo.
Los nodos siguen guardando estructura, sin ejecutar acciones por sí mismos.

`stringify()` convierte los valores al formato de Lox:

| Valor | Texto que imprime |
| --- | --- |
| `None`, que representa `nil` | `nil` |
| `True` | `true` |
| `False` | `false` |
| Número `5.0` | `5` |
| Cadena `"hola"` | `hola` |

## 6. ¿Por qué cambiamos la CLI y el impresor del AST?

La [CLI](../src/mylox/cli.py) ahora hace este recorrido:

```text
Texto del archivo
    ↓ Lexer.run()
Lista de tokens
    ↓ Parser.parse()
Lista de sentencias AST
    ↓ Interpreter.interpret()
Acciones del programa
```

`run_actions()` ya no llama a `print()` con el resultado de una expresión.
La salida del programa aparece cuando el intérprete ejecuta un nodo `PrintStmt`.

El [Impresor](../src/mylox/printing.py) también entiende los nodos nuevos y la lista del programa.
Así, `--tree` puede mostrar todas las sentencias, usando el mismo Visitor para producir una descripción en lugar de ejecutarlas.

**Idea para recordar:** una expresión calcula un valor; una sentencia usa ese cálculo para realizar una acción; un programa ejecuta una secuencia de sentencias.
