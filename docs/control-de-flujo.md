# CONTROL DE FLUJO: IF, WHILE Y FOR

## 1. ¿Qué significa controlar el flujo de un programa?

Sin estas construcciones, `interpret()` ejecuta las sentencias una detrás de otra.
El control de flujo permite elegir qué sentencias ejecutar o repetirlas varias veces.

```lox
var edad = 20;
if (edad >= 18) {
    print "mayor";
} else {
    print "menor";
}
```

Este programa imprime `mayor`.
Ambas ramas están presentes en el texto y en el AST, pero durante la ejecución se elige una sola.

## 2. ¿Dónde intervienen lexer, parser, AST e intérprete?

El [lexer](../src/mylox/pipeline/lexer.py) ya reconoce las palabras `if`, `else`, `while` y `for`, además de paréntesis, llaves y `;`.

El [parser](../src/mylox/pipeline/parser.py) usa esos tokens para construir condiciones y cuerpos.
Los cuerpos contienen otras sentencias; por eso un `if` puede contener un bloque, y ese bloque puede contener otro `if` o un bucle.

En [nodes.py](../src/mylox/nodes.py), agregamos:

| Nodo | Campos |
| --- | --- |
| `IfStmt` | `condition`, `then_branch`, `else_branch` opcional |
| `WhileStmt` | `condition`, `body` |

El [intérprete](../src/mylox/interpreter.py) evalúa las condiciones cuando ejecuta esos nodos.
El parser construye la estructura una vez; el intérprete decide cómo recorrerla durante la ejecución.

## 3. ¿Cómo funciona if/else?

La forma que reconoce `_if_statement()` es:

```text
"if" "(" expresión ")" sentencia ("else" sentencia)?
```

Los paréntesis alrededor de la condición son obligatorios. Las llaves se usan cuando queremos un bloque con varias instrucciones.
También se puede usar una sentencia individual como cuerpo:

```lox
if (true) print "sí";
```

El AST del ejemplo de la edad tiene esta forma abreviada:

```text
IfStmt
├── condition: Binary(Variable("edad"), >=, Literal(18))
├── then_branch: BlockStmt([PrintStmt("mayor")])
└── else_branch: BlockStmt([PrintStmt("menor")])
```

`IfStmt.accept(interpreter)` llama a `visit_if_stmt()`.
Ese método evalúa la condición y ejecuta la rama correspondiente mediante su propio `accept()`.
Si la condición es falsa y no hay `else`, sigue con la próxima sentencia del programa.

### ¿Qué valores cuentan como verdaderos?

`is_truthy()` aplica la regla de Lox:

| Valor | ¿La condición se considera verdadera? |
| --- | --- |
| `false` | No |
| `nil` | No |
| `0` | Sí |
| `""` | Sí |
| Cualquier otro valor | Sí |

Por eso usamos `is_truthy()`: convertir directamente a `bool` de Python daría otro comportamiento para `0` y para la cadena vacía.

### ¿A qué if pertenece un else?

En este ejemplo, `else` pertenece al `if` interior:

```lox
if (true)
    if (false) print "uno";
    else print "dos";
```

La salida es `dos`.
Esto ocurre porque `_if_statement()` construye recursivamente el cuerpo: el parser del `if` interior consume su `else` antes de volver al exterior.
Las llaves permiten expresar otra agrupación cuando la necesitamos.

## 4. ¿Cómo funciona while?

Un `while` repite el cuerpo mientras su condición siga siendo verdadera:

```lox
var i = 0;
while (i < 3) {
    print i;
    i = i + 1;
}
print i;
```

La salida es:

```text
0
1
2
3
```

`_while_statement()` construye la condición y una sentencia para el cuerpo.
El nodo resultante contiene algo equivalente a:

```text
WhileStmt
├── condition: Binary(Variable("i"), <, Literal(3))
└── body: BlockStmt
    ├── PrintStmt(Variable("i"))
    └── ExprStmt(Assign("i", Binary(Variable("i"), +, Literal(1))))
```

`visit_while_stmt()` vuelve a evaluar **el mismo árbol de la condición** antes de cada vuelta:

| Momento | Valor de `i` | Resultado de `i < 3` | Acción |
| --- | --- | --- | --- |
| Primera comprobación | `0` | `true` | Imprime `0` y guarda `1` |
| Segunda comprobación | `1` | `true` | Imprime `1` y guarda `2` |
| Tercera comprobación | `2` | `true` | Imprime `2` y guarda `3` |
| Cuarta comprobación | `3` | `false` | Sale del bucle |

El AST se reutiliza, pero la lectura de `i` obtiene su valor actualizado.
Si la condición ya es falsa al principio, el cuerpo se ejecuta cero veces.

Cada ejecución de un cuerpo con llaves crea un ambiente de bloque.
La asignación de `i` alcanza el ambiente exterior porque `i` fue declarada antes del bucle.

## 5. ¿Cómo funciona for?

Un `for` reúne el inicio, la condición y el avance en su encabezado:

```lox
for (var i = 0; i < 3; i = i + 1) print i;
```

La salida es `0`, `1` y `2`, cada número en una línea.
El orden de ejecución es:

1. Ejecutar `var i = 0;` una sola vez.
2. Evaluar `i < 3`.
3. Si es verdadera, ejecutar `print i;`.
4. Ejecutar `i = i + 1`.
5. Volver al paso 2.

La condición se comprueba antes del cuerpo, y el avance ocurre después de cada ejecución del cuerpo.

### ¿Por qué no agregamos un nodo ForStmt?

`_for_statement()` transforma el `for` en nodos que ya sabemos ejecutar.
Esta transformación de una construcción a otras más simples se suele llamar **desazucarado**.

El ejemplo anterior equivale a:

```lox
{
    var i = 0;
    while (i < 3) {
        print i;
        i = i + 1;
    }
}
```

El parser construye directamente ese AST:

```text
BlockStmt
├── VarDecl("i", Literal(0))
└── WhileStmt
    ├── condition: Binary(Variable("i"), <, Literal(3))
    └── body: BlockStmt
        ├── PrintStmt(Variable("i"))
        └── ExprStmt(Assign("i", Binary(Variable("i"), +, Literal(1))))
```

Si el cuerpo original del `for` era un bloque, se conserva como un nodo dentro del bloque que agrega el incremento.
El intérprete recibe `BlockStmt` y `WhileStmt`, por lo que puede ejecutarlo con los visitantes ya implementados.

El bloque exterior se agrega cuando hay un inicializador. Así, un `var i` declarado en el encabezado queda dentro del ámbito del bucle.
Leer `i` después de ese `for` produce un error de variable indefinida.

### ¿Qué partes del encabezado se pueden omitir?

| Parte omitida | Qué hace el parser |
| --- | --- |
| Inicializador | No agrega una sentencia inicial |
| Condición | Usa `Literal(True)` |
| Avance | No agrega una sentencia al final del cuerpo |

Por ejemplo, este bucle termina porque el avance está escrito dentro del cuerpo:

```lox
var i = 0;
for (; i < 2;) {
    print i;
    i = i + 1;
}
```

La salida es `0` y `1`.
Los dos `;` del encabezado siguen siendo necesarios aunque se omitan componentes.
Omitir la condición la convierte en verdadera; el bucle necesita otra forma de terminar para no repetirse indefinidamente.

## 6. El recorrido completo

```text
Texto con if, while o for
    ↓ lexer
Tokens de palabras reservadas, condiciones y cuerpos
    ↓ parser
IfStmt, WhileStmt y bloques
    ↓ Visitor del intérprete
Evaluar condiciones y ejecutar los cuerpos elegidos
```

Las pruebas de [test_statements.py](../tests/test_statements.py) cubren selección de ramas, asociación de `else`, repetición, incremento del `for` y ámbito de su variable inicial.
Además, `1-flow.lox` pasó la verificación de salida exacta, stderr vacío y código de salida `0`.

**Idea para recordar:** `if` elige una rama; `while` reevalúa una condición para repetir; el parser convierte `for` en un inicio seguido de un `while`.
