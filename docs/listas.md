# Listas mutables

Agregamos listas como extra de la entrega final, con las mismas operaciones
en tree-walk y bytecode.

```lox
var numeros = [10, 20, 30];
numeros[1] = 99;
numeros.push(40);
print numeros.length;
print numeros.pop();
print numeros;
```

Imprime `4`, `40` y `[10, 99, 30]`.

## Operaciones

| Operación | Resultado |
| --- | --- |
| `[a, b]` | Crea una lista y evalúa los elementos de izquierda a derecha |
| `lista[indice]` | Lee un elemento |
| `lista[indice] = valor` | Modifica un elemento y devuelve el valor asignado |
| `lista.length` | Devuelve la cantidad de elementos |
| `lista.push(valor)` | Agrega al final y devuelve `nil` |
| `lista.pop()` | Quita y devuelve el último elemento |

Los elementos pueden ser de cualquier tipo, incluidas otras listas.
Se pueden encadenar llamadas, propiedades e índices:
`crearEquipo()[0].inventario[1] = objeto;`.

Los índices empiezan en cero y deben ser enteros. Índices negativos,
fraccionarios, booleanos o fuera de rango producen un error de runtime.
También fallan `pop()` sobre una lista vacía y los intentos de reemplazar
`length`, `push` o `pop`.

Una asignación evalúa receptor, índice y valor, una vez cada uno, antes de
validar y escribir. Los métodos ligados conservan su lista:
`var agregar = lista.push; agregar(5);` sigue funcionando si después se
reasigna la variable `lista`.

## Referencias e igualdad

```lox
var a = [1];
var b = a;
b[0] = 7;
print a;
print a == b;
print a == [7];
```

Imprime `[7]`, `true` y `false`. Asignar o pasar una lista comparte la
referencia. La igualdad compara identidad, como ocurre con funciones e
instancias. Una lista vacía es verdadera, según la regla de Lox.

`print` conserva comillas en los strings contenidos. Las referencias
circulares se muestran como `[...]`:
`var a = []; a.push(a); print a;` imprime `[[...]]`.

## Implementación

`LoxList` usa una lista de Python y reúne la validación de índices y las
operaciones. Adaptamos la igualdad, el valor de verdad y los índices para
seguir las reglas anteriores. Los métodos nativos quedan ligados a una
lista; cada backend comprueba la aridad y agrega la posición a los errores.

El AST tiene `ListLiteral`, `Index` e `IndexSet`; el resolver visita sus
expresiones y el intérprete las evalúa. El compilador emite:

| Instrucción | Pila antes → después |
| --- | --- |
| `OP_LIST n` | `e0 … eN` → `lista` |
| `OP_GET_INDEX` | `lista indice` → `valor` |
| `OP_SET_INDEX` | `lista indice valor` → `valor` |

El tamaño del literal ocupa un byte: ambos backends admiten hasta 255
elementos por literal. `push` permite crecer después. Las listas se recorren
con los bucles existentes; no hay slicing ni indexación de strings.

## Demo y pruebas

[combate.lox](../examples/combate.lox) mantiene una lista de participantes y
retira a los derrotados con `pop` y asignación por índice. Termina con
`Ganador: Ada` en ambos backends.

```sh
uv run mylox examples/combate.lox --backend bytecode
uv run pytest tests/test_lists.py tests/test_backend_regressions.py
```

Las pruebas cubren mutación, referencias compartidas, ciclos, métodos ligados,
orden de evaluación, closures, errores y el combate completo. También
comprueban el AST, el desensamblado y el balance de la pila.
