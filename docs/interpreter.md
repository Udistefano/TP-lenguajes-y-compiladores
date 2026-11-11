# Lexer, parser e intérprete

El tree-walk procesa el programa en cuatro pasos: texto → tokens → AST →
resolución de variables → ejecución. El backend bytecode comparte el lexer;
su recorrido se explica en [bytecode](bytecode.md).

## Lexer

[Lexer.run()](../src/mylox/pipeline/lexer.py) recibe el texto y devuelve tokens
terminados en `EOF`. Cada [Token](../src/mylox/tokens.py) guarda su tipo,
lexema, valor literal y posición de origen.

`start` marca el comienzo del token y `current` el próximo carácter a leer.
El lexema sale de `source[start:current]`. Los números usan dígitos ASCII y
se convierten a `float`; los identificadores se leen completos antes de
consultar `KEYWORDS`. Así, `trueman` es un identificador, no `true` y `man`.

Los espacios y comentarios `//` se descartan. Para operadores como `!=`, el
lexer mira el carácter siguiente antes de elegir el tipo de token.

## Parser y precedencia

[Parser.parse()](../src/mylox/pipeline/parser.py) lee declaraciones y
sentencias hasta `EOF`. Usa descenso recursivo: cada regla de expresiones
llama a la de mayor precedencia para construir sus operandos.

De menor a mayor precedencia: asignación, `or`, `and`, igualdad, comparación,
suma/resta, multiplicación/división/módulo, unarios, llamadas/propiedades/índices
y expresiones primarias.

Para `print 1 + 2 * 3;`, el árbol queda así:

```text
PrintStmt
└── Binary (+)
    ├── Literal(1)
    └── Binary (*)
        ├── Literal(2)
        └── Literal(3)
```

`_factor()` arma la multiplicación antes de que `_term()` termine la suma.
Los bucles de esas reglas agrupan los operadores por izquierda:
`5 - 3 - 1` es `(5 - 3) - 1`. La asignación es recursiva por derecha:
`a = b = 3` es `a = (b = 3)`. Los paréntesis crean un nodo `Grouping`.

## AST y Visitor

Los [nodos](../src/mylox/nodes.py) son dataclasses inmutables con `slots`.
Guardan la estructura del programa. Cada `accept()` llama al método del
visitante que corresponde al nodo; por ejemplo, `Binary.accept()` hace:

```python
return visitor.visit_binary(self)
```

[Interpreter.visit_binary()](../src/mylox/interpreter.py) evalúa izquierda
y derecha y aplica el operador. [Impresor.visit_binary()](../src/mylox/printing.py)
produce una descripción del mismo árbol. Elegimos este Visitor en lugar del
`singledispatchmethod` usado por plox.

Antes de ejecutar, `Interpreter.interpret()` usa `BindingResolver` para
vincular las referencias locales con sus ámbitos. Después recorre las
sentencias en orden. En el ejemplo, calcula primero `2 * 3`, suma `1` y
`PrintStmt` imprime `7`.

Los detalles de ejecución están en [sentencias](statements.md),
[variables](variables.md) y [funciones y closures](funciones-y-closures.md).
