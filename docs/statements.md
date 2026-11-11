# Sentencias y print

```lox
2 + 3;
print 2 + 3;
```

Las dos sentencias calculan `5`. La primera descarta el resultado y la
segunda lo imprime. El lexer conserva `;` como `SEMICOLON`; los saltos de
línea no separan sentencias.

## Parseo

[Parser.parse()](../src/mylox/pipeline/parser.py) devuelve una lista de nodos
y lee hasta `EOF`. Un archivo vacío es válido. Si hay un error en cualquier
sentencia, falla antes de ejecutar el programa: `print 1; print 2 +;` no
imprime nada.

`_statement()` reconoce `print expresión;` y, si no encuentra otra forma de
sentencia, intenta leer `expresión;`. El AST del ejemplo contiene un
`ExprStmt` y un `PrintStmt`, ambos con una expresión `Binary`.

## Ejecución

El [intérprete](../src/mylox/interpreter.py) recorre la lista en orden.
`visit_expr_stmt()` evalúa y descarta; `visit_print_stmt()` evalúa, convierte
con `stringify()` y escribe una línea.

| Valor interno | Salida |
| --- | --- |
| `None` | `nil` |
| `True` / `False` | `true` / `false` |
| `5.0` | `5` |
| `"hola"` | `hola` |

La CLI imprime valores cuando el programa ejecuta `print`. El modo `--tree`
usa el [Impresor](../src/mylox/printing.py) para mostrar el AST completo.
Las pruebas están en [test_statements.py](../tests/test_statements.py).
