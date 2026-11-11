# Variables y ámbitos

```lox
var puntos = 10;
puntos = puntos + 5;
print puntos;
```

`var` declara, una referencia lee y `=` modifica una variable existente.
El ejemplo imprime `15`. Sin inicializador, `var dato;` guarda `nil`.

## Parseo y asignación

El [parser](../src/mylox/pipeline/parser.py) reconoce
`var nombre (= expresión)? ;`. Los nodos del AST son:

| Nodo | Datos |
| --- | --- |
| `VarDecl` | Nombre e inicializador opcional |
| `Variable` | Nombre que se lee |
| `Assign` | Nombre y expresión del nuevo valor |
| `BlockStmt` | Declaraciones y sentencias del bloque |

Los nombres conservan su token para informar línea y columna en los errores.
La asignación devuelve el valor guardado y se agrupa por derecha:
`a = b = 3` asigna primero a `b` y después a `a`.

El destino puede ser una variable, una propiedad o un índice de lista.
`(1 + 2) = 3;` es un error de sintaxis. `==` compara valores; no asigna.

## Ambientes y resolución

[Env](../src/mylox/env.py) guarda un diccionario `values` y una referencia
`enclosing` al ambiente exterior. El ambiente global no tiene padre.

| Método | Acción |
| --- | --- |
| `define(name, value)` | Define o reemplaza el nombre en este ambiente |
| `get(name)` | Busca en este ambiente y sus padres |
| `assign(name, value)` | Actualiza el primer ambiente que contiene el nombre |
| `get_local(name, levels)` | Lee en el ambiente elegido por el resolver |
| `assign_local(name, value, levels)` | Modifica ese ambiente |

Leer o asignar un nombre inexistente produce `LoxRuntimeError`. Una variable
con `nil`, `false` o `0` sigue estando definida.

[BindingResolver](../src/mylox/resolver.py) fija el ámbito de cada referencia
antes de ejecutar. El intérprete usa `get_local()` y `assign_local()` para
los locales, y accede al ambiente global para el resto. Esto evita que una
declaración posterior cambie el ámbito de un [closure](funciones-y-closures.md).

## Inicializadores y redeclaraciones

Ambos backends evalúan el inicializador antes de definir el nombre:

```lox
var a = 1;
{
    var a = a + 1;
    print a;
}
print a;
```

Imprime `2` y `1`. Si no existe un nombre anterior, leerlo falla en runtime.
Una redeclaración en el mismo ámbito reemplaza la variable; en bytecode
reutiliza su slot, así que las funciones que la capturaron ven el nuevo valor.
Esto se aplica a `var`, `fun` y `class`. Si se repite un parámetro, su nombre
queda asociado al último argumento recibido.

Conservamos estas reglas del parcial. El Lox del libro rechaza las
redeclaraciones locales y las lecturas del nombre que se está inicializando.
Las redeclaraciones globales están permitidas en ambos.

## Bloques

Cada bloque crea un `Env` cuyo padre es el ambiente activo. Una declaración
local oculta el nombre exterior; una asignación modifica el ámbito que eligió
el resolver.

`execute_block()` guarda el ambiente activo, ejecuta el cuerpo en el nuevo
y restaura el anterior con `finally`. La restauración ocurre también ante
un error o un `return`. Las funciones usan la misma operación para sus cuerpos.

La VM representa esos ámbitos con slots de la pila y cierra las capturas al
salir. Los detalles están en [bytecode](bytecode.md).
