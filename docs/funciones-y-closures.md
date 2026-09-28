# Funciones, retornos y closures

## Funciones y llamadas

```lox
fun doble(x) {
    return x * 2;
}
print doble(3);
```

La salida es `6`.

- **Lexer:** reconoce `fun`, `return`, nombres, paréntesis y llaves. Ya lo hacía.
- **Parser:** `_function_declaration()` construye `FunctionDecl`; `_call()` construye `Call`; `_return_statement()` construye `ReturnStmt`.
- **AST:** conserva nombre, parámetros, cuerpo y argumentos. Todos los nodos mantienen `accept()` y Visitor con double dispatch.
- **Intérprete:** `visit_function_decl()` crea una `Function` y la guarda en el ámbito actual. El cuerpo se ejecuta al llamar.

Referencias: [parser](../src/mylox/pipeline/parser.py), [nodos](../src/mylox/nodes.py), [intérprete](../src/mylox/interpreter.py).

`visit_call()` evalúa la función y sus argumentos de izquierda a derecha.
Después verifica que sea invocable y que la cantidad de argumentos coincida
con `Function.arity`. Una llamada inválida produce `LoxRuntimeError`.

## El ámbito de cada invocación

[Function.call()](../src/mylox/function.py) conserva la implementación de la
rama de funciones. Crea `Env(enclosing=self.closure)`, define los parámetros
y ejecuta el cuerpo con `execute_block()`.

Cada llamada tiene variables locales propias. El padre es el ámbito donde
la función fue declarada. Ese enlace permite acceder a variables capturadas
y llamar recursivamente a la misma función.

## Cómo sale return de un cuerpo anidado

`visit_return_stmt()` evalúa el valor y lanza `ReturnValue`. La excepción
atraviesa bloques, `if` y bucles. Los `finally` de `execute_block()` restauran
los ambientes; `Function.call()` captura la excepción y devuelve su valor.

`return;` y terminar el cuerpo sin return devuelven `nil`. Un return fuera
de una función se detecta antes de ejecutar el programa.

## Closure: conservar variables después de una llamada

```lox
fun crear() {
    var n = 0;
    fun siguiente() {
        n = n + 1;
        return n;
    }
    return siguiente;
}
var contador = crear();
print contador();
print contador();
```

La salida es `1` y después `2`. `siguiente` conserva una referencia al Env
de `crear`; por eso `n` sigue existiendo y las llamadas comparten su valor.
Otro `crear()` produce un contador independiente.

## Por qué hace falta resolver los nombres antes

```lox
var a = "global";
{
    fun leer() { return a; }
    var a = "local";
    print leer();
}
```

La salida debe ser `global`: la variable local no existía al declarar `leer`.
Buscar sólo por nombre en una cadena de diccionarios mutables encontraría
el nuevo `a` local y cambiaría el significado de la función.

[BindingResolver](../src/mylox/resolver.py) recorre el AST antes de ejecutarlo.
Registra los nombres locales en orden y vincula cada `Variable` o `Assign`
con una distancia de ámbitos: cero es el Env activo, uno su padre, etc.
Si no hay vínculo local, el intérprete usa el global.

[Env.get_local() y Env.assign_local()](../src/mylox/env.py) acceden directamente
al ámbito elegido. El vínculo se mantiene aunque después aparezca otra
declaración con el mismo nombre; los valores capturados siguen siendo mutables.

## Verificación

[Tests de integración](../tests/test_functions_integration.py): declaraciones,
retornos, recursión, aridad, evaluación de argumentos y restauración de ámbitos.

[Tests de closures](../tests/test_closures.py): captura con estado, contadores
independientes, nombres sombreados después y funciones usadas entre programas.

[Verificador estricto](../tests/strict_real_tests.py): los cinco programas de
`plox/real-tests/` con salida exacta, stderr vacío y código de salida 0.
