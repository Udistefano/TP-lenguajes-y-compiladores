# INTERPRETER:


## 1. ¿Qué recibe el lexer y qué entrega?

El [lexer](../src/mylox/pipeline/lexer.py) recibe un `str` con el programa. Por ejemplo:

```lox
12.5 + 2 * 3
```

Todavía no intenta calcular nada ni decidir qué operación va primero. Su único trabajo es separar el texto en piezas reconocibles, llamadas *tokens*:

```text
NUMBER("12.5", valor=12.5)
PLUS("+")
NUMBER("2", valor=2.0)
STAR("*")
NUMBER("3", valor=3.0)
EOF
```

Cada [Token](../src/mylox/tokens.py) guarda tres ideas distintas:

- `kind`: qué clase de pieza es (`NUMBER`, `PLUS`, `IDENTIFIER`).
- `lexeme`: los caracteres originales, por ejemplo `"12.5"`.
- `literal`: el valor ya convertido, por ejemplo el número Python `12.5`. Los operadores no necesitan ese valor.
- `line` y `column`: dónde empezó, para informar errores.

Una distinción importante: el lexer reconoce que `+` es un token `PLUS`, pero todavía no sabe qué números va a sumar.

### Cómo avanza por el texto

El lexer mantiene dos índices:

```text
source:  1 2 . 5   +   2
         ↑
       start
         ↑
       current
```

`start` marca dónde comenzó el token actual. `current` marca el próximo carácter que va a leer. Al terminar de reconocer un token, corta `source[start:current]` para obtener su `lexeme`. Además lleva la línea y columna actuales.

En cada vuelta de `run()`:

1. Guarda la posición inicial del próximo token.
2. `_scan_token()` consume el primer carácter con `_advance()`.
3. Según ese carácter, decide si el token ya está completo o si debe seguir leyendo.
4. Agrega el token a la lista.
5. Al terminar toda la fuente, agrega `EOF`.

Por ejemplo, al encontrar `1`, `_scan_token()` llama a `_scan_number()`. Este sigue consumiendo dígitos y, si encuentra `.` seguido de otro dígito, también consume la parte decimal. Finalmente convierte el texto `"12.5"` a `float(12.5)`.

Con nombres ocurre algo parecido. Si encuentra la `t` de `trueman`, consume **todo** `trueman` y recién después consulta `KEYWORDS`. Así evita separar erróneamente `true` + `man`. Si el texto completo está en `KEYWORDS`, es una palabra reservada; si no, es `IDENTIFIER`.

Los espacios se consumen sin generar tokens. Con `//`, consume el resto de la línea como comentario. Para `!=`, mira el carácter siguiente: produce `BANG_EQUAL` si hay `=`, o `BANG` si no lo hay. Esa mirada anticipada es el *lookahead*.

## 2. ¿Por qué los tokens no alcanzan?

Considerá:

```lox
1 + 2 * 3
```

El lexer entrega una secuencia lineal:

```text
NUMBER PLUS NUMBER STAR NUMBER EOF
```

Esa secuencia todavía no indica claramente si queremos:

```text
(1 + 2) * 3 = 9
```

o:

```text
1 + (2 * 3) = 7
```

El [parser](../src/mylox/pipeline/parser.py) transforma esa lista lineal en un **árbol** que deja explícita la agrupación:

```text
        Binary (+)
        /        \
 Literal(1)    Binary (*)
               /        \
        Literal(2)    Literal(3)
```

La raíz es `+`. Para poder sumar, primero hay que conocer el valor de su rama derecha; esa rama es la multiplicación. Por eso el árbol representa `1 + (2 * 3)`.

Se llama árbol de sintaxis *abstracta* porque conserva lo necesario para entender la operación, sin guardar cada detalle del texto. Por ejemplo, los espacios no son nodos.

## 3. ¿Cómo construye ese árbol el parser?

El parser también tiene un cursor, pero avanza por **tokens**, no por caracteres. `_peek()` mira el token actual, `_advance()` lo consume y `_match()` comprueba si pertenece a los tipos esperados.

Las reglas de expresiones representan niveles de precedencia. Sus nombres se leen aproximadamente así:

```text
asignación
  or
    and
      igualdad
        comparación
          suma/resta
            multiplicación/división/módulo
              unario
                llamada
                  literal, variable o paréntesis
```

Dentro del recorrido de una expresión, `_assignment()` llama a `_or()`, `_or()` a `_and()` y `_and()` a `_equality()`. Cada nivel llama al siguiente para construir sus operandos completos. `parse()` empieza por las declaraciones y sentencias del programa completo.

Sigamos `1 + 2 * 3`:

1. `_term()` necesita su primer operando y llama a `_factor()`.
2. `_factor()` llega a `_primary()` y obtiene `Literal(1)`.
3. `_term()` ve `+` y necesita construir **todo** el operando derecho, así que vuelve a llamar a `_factor()`.
4. Esta vez `_factor()` obtiene `Literal(2)`, ve `*`, obtiene `Literal(3)` y construye `Binary(2, *, 3)`.
5. `_term()` recibe ese árbol completo y construye `Binary(1, +, Binary(2, *, 3))`.

La multiplicación queda más profunda porque `_factor()` la resolvió como estructura antes de que `_term()` armara la suma.

Los `while` dentro de `_term()` y `_factor()` también definen la **asociatividad**. Con `5 - 3 - 1`, el parser va reemplazando el árbol acumulado:

```text
primero:  Binary(5, -, 3)
después:  Binary(Binary(5, -, 3), -, 1)
```

Eso representa `(5 - 3) - 1`, como esperamos.

Los paréntesis cambian la estructura: al ver `(`, `_primary()` llama de nuevo a `_expression()` para parsear lo que está adentro y exige luego `)`. El resultado se envuelve en un nodo `Grouping`.

## 4. ¿Qué son los nodos y dónde entra Visitor?

En [nodes.py](../src/mylox/nodes.py), cada clase representa una forma posible de expresión:

- `Literal(3.0)`: un valor.
- `Unary(-, Literal(3.0))`: un operador y un operando.
- `Binary(Literal(1.0), +, Literal(2.0))`: dos operandos y un operador.
- `Grouping(...)`: una expresión entre paréntesis.

Un nodo `Binary` **no suma por sí mismo**. Solo guarda la estructura: izquierda, operador y derecha. Esto permite usar el mismo árbol para distintas tareas.

Por ejemplo, ambos objetos recorren el mismo AST:

```python
tree.accept(Impresor())     # produce una descripción del árbol
tree.accept(Interpreter())  # produce un valor de Lox
```

El mecanismo de *double dispatch* es esta llamada dentro de `Binary.accept()`:

```python
return visitor.visit_binary(self)
```

Hay dos decisiones encadenadas:

1. El tipo de nodo (`Binary`) decide llamar a `visit_binary`.
2. El visitante concreto (`Impresor` o `Interpreter`) decide qué significa visitar ese `Binary`.

Así, `Impresor.visit_binary()` arma texto, mientras que `Interpreter.visit_binary()` evalúa ambas ramas y aplica el operador.

## 5. El recorrido completo

Con `1 + 2 * 3`:

```text
Texto fuente
   ↓ lexer
[NUMBER, PLUS, NUMBER, STAR, NUMBER, EOF]
   ↓ parser
Binary(1, +, Binary(2, *, 3))
   ↓ intérprete
1 + (2 * 3)
   ↓
7.0
```

El [intérprete](../src/mylox/interpreter.py) recorre el árbol de forma recursiva. Para el `Binary` exterior evalúa la izquierda (`1`), luego la derecha. Evaluar la derecha requiere evaluar su propio `Binary` (`2 * 3`), que devuelve `6`. Recién entonces el exterior suma `1 + 6`.

Este recorrido explica la evaluación de una expresión dentro de una sentencia. `Parser.parse()` devuelve una lista de sentencias y procesa el programa hasta `EOF`. Antes de ejecutar, `Interpreter.interpret()` recorre el AST con `BindingResolver` para vincular las variables locales. Para imprimir el resultado del ejemplo, el programa completo es `print 1 + 2 * 3;` y su salida es `7`. La explicación continúa en [statements.md](statements.md), [variables.md](variables.md), [control-de-flujo.md](control-de-flujo.md) y [funciones-y-closures.md](funciones-y-closures.md).

La separación sigue siendo la misma: **el lexer reconoce piezas, el parser decide cómo se agrupan y el visitante decide qué hacer con el árbol resultante**.
