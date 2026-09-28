# VARIABLES, ASIGNACIONES Y ÁMBITOS

## 1. ¿Qué significa guardar un valor en una variable?

Considerá:

```lox
var puntos = 10;
puntos = puntos + 5;
print puntos;
```

La salida es:

```text
15
```

Hay tres operaciones distintas:

1. **Declarar:** `var puntos = 10;` crea el nombre `puntos` en el ámbito actual y guarda su valor inicial.
2. **Leer:** el `puntos` que aparece a la derecha de `=` consulta el valor guardado.
3. **Asignar:** `puntos = ...` reemplaza el valor de una variable existente.

El nombre y el valor tienen trabajos diferentes. El nombre permite encontrar un lugar de almacenamiento; el valor es lo que usamos al calcular.

## 2. ¿Dónde intervienen lexer, parser y AST?

El [lexer](../src/mylox/pipeline/lexer.py) reconoce `var` como `VAR` y `puntos` como `IDENTIFIER`:

```text
VAR IDENTIFIER("puntos") EQUAL NUMBER(10) SEMICOLON
IDENTIFIER("puntos") EQUAL IDENTIFIER("puntos") PLUS NUMBER(5) SEMICOLON
PRINT IDENTIFIER("puntos") SEMICOLON
EOF
```

El lexer reconoce los nombres, pero no comprueba si ya están declarados. Eso depende de lo que ocurra al ejecutar el programa.

El [parser](../src/mylox/pipeline/parser.py) construye estos nodos. Los nombres se muestran abreviados; en el código se guardan como objetos `Token`:

```text
VarDecl("puntos", Literal(10))
ExprStmt(
    Assign("puntos", Binary(Variable("puntos"), +, Literal(5)))
)
PrintStmt(Variable("puntos"))
```

Cada nodo de [nodes.py](../src/mylox/nodes.py) tiene una responsabilidad:

| Nodo | Qué guarda |
| --- | --- |
| `VarDecl` | El token del nombre y una expresión inicializadora opcional |
| `Variable` | El token del nombre que queremos leer |
| `Assign` | El token del nombre y la expresión del nuevo valor |
| `BlockStmt` | Una lista de declaraciones y sentencias |

Guardar el token también conserva la línea y columna para informar errores de variables indefinidas.

## 3. ¿Cómo se parsean las declaraciones y las asignaciones?

`_declaration()` reconoce esta forma:

```text
"var" nombre ("=" expresión)? ";"
```

El inicializador es opcional. Por eso este programa imprime `nil`:

```lox
var dato;
print dato;
```

La asignación es una **expresión**: además de guardar un valor, devuelve ese mismo valor.
Esto permite escribir:

```lox
var a;
var b;
print a = b = 3;
print a;
print b;
```

Las tres líneas de salida son `3`.

`_assignment()` primero construye la expresión que aparece a la izquierda.
Si encuentra `=`, llama recursivamente a `_assignment()` para construir la derecha.
Esa recursión hace que la asignación se agrupe **de derecha a izquierda**:

```text
a = (b = 3)
```

Primero se asigna `3` a `b`. Esa asignación devuelve `3`, que luego se asigna a `a`.

El parser también exige que el destino sea un nodo `Variable`.
Por eso `(1 + 2) = 3;` es un error de sintaxis: una suma no identifica una variable donde guardar el resultado.

`=` y `==` son operaciones diferentes: `=` asigna; `==` compara valores.

## 4. ¿Qué es un ambiente, o Env?

Un [Env](../src/mylox/env.py) es el objeto que guarda las variables de un ámbito.
Su diccionario `values` relaciona nombres con valores:

```text
values = {
    "puntos": 15.0,
    "dato": None
}
```

Además, `enclosing` apunta al ambiente exterior. El ambiente global tiene `enclosing = None`.

Sus operaciones son:

| Método | Acción |
| --- | --- |
| `define(name: str, value)` | Guarda el nombre en este ambiente |
| `get(name: Token)` | Busca el nombre aquí y luego en los ambientes exteriores |
| `assign(name: Token, value)` | Actualiza el primer ambiente de la cadena que contiene el nombre |

`get()` y `assign()` usan `name.lexeme` como clave del diccionario.
Si llegan al final de la cadena sin encontrar el nombre, lanzan `LoxRuntimeError`.

La búsqueda comprueba si la clave existe. Una variable que contiene `nil`, `false` o `0` sigue siendo una variable definida.

En nuestra implementación, declarar otra vez un nombre en el mismo ambiente reemplaza su entrada. Declararlo dentro de un bloque crea una entrada en otro ambiente.

## 5. ¿Cómo se ejecuta el ejemplo inicial?

El [intérprete](../src/mylox/interpreter.py) comienza con un ambiente global:

```python
self.globals = Env()
self.environment = self.globals
```

`environment` es el ambiente activo. Sigamos las tres sentencias:

1. `visit_var_decl()` evalúa `Literal(10)` y llama a `environment.define("puntos", 10.0)`.
2. `visit_assign()` evalúa primero su expresión derecha. `visit_variable()` obtiene `10`, y la suma produce `15`.
3. `visit_assign()` llama a `environment.assign(...)`, guarda `15` y devuelve ese valor. La sentencia de expresión descarta ese resultado.
4. `visit_print_stmt()` lee `puntos` nuevamente y escribe `15`.

Cada llamada se selecciona mediante el `accept()` del nodo correspondiente, conservando el Visitor con double dispatch.

## 6. ¿Qué cambia al entrar en un bloque?

Las llaves crean un ámbito propio:

```lox
var x = 1;
var y = 0;
{
    var x = 2;
    y = x;
    print x;
}
print x;
print y;
```

La salida es:

```text
2
1
2
```

El parser usa `_block()` para reunir los nodos que están entre `{` y `}`.
Al ejecutar ese `BlockStmt`, el intérprete crea un ambiente cuyo padre es el ambiente activo:

```text
Ambiente del bloque             Ambiente global
values: {x: 2}  ── enclosing ──→ values: {x: 1, y: 0}
```

Dentro del bloque:

- `var x = 2;` define un `x` local. Al leer `x`, la búsqueda lo encuentra antes de llegar al global. Esto se llama **sombrear** un nombre.
- `y = x;` lee el `x` local, pero no encuentra un `y` local. `assign()` continúa hacia el ambiente global y modifica su `y`.

Al salir del bloque, el ambiente activo vuelve a ser el global. Su `x` sigue valiendo `1`, y su `y` ahora vale `2`.
Una variable declarada solamente dentro del bloque deja de estar disponible desde afuera.

## 7. ¿Por qué execute_block() usa try/finally?

`execute_block(statements, environment)` hace tres cosas:

1. Guarda el ambiente que estaba activo.
2. Activa el ambiente recibido y ejecuta las sentencias del cuerpo.
3. Restaura el ambiente anterior en un `finally`.

`finally` se ejecuta también si una sentencia lanza una excepción.
Así, un error dentro del bloque no deja al intérprete usando por accidente el ambiente interno.
Esta misma operación queda disponible para que las funciones ejecuten sus cuerpos al integrarse.

**Idea para recordar:** declarar agrega un nombre al ámbito actual; leer busca hacia afuera; asignar modifica el primer nombre existente que encuentra; un bloque agrega un ambiente a esa cadena.
