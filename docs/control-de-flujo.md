# Control de flujo

## if y else

```lox
var edad = 20;
if (edad >= 18) {
    print "mayor";
} else {
    print "menor";
}
```

Imprime `mayor`. El [parser](../src/mylox/pipeline/parser.py) exige paréntesis
en la condición y admite una sentencia o un bloque como cuerpo. Construye
`IfStmt(condition, then_branch, else_branch)`; la última rama es opcional.

`visit_if_stmt()` evalúa la condición y ejecuta la rama elegida. `is_truthy()`
considera falsos solamente `false` y `nil`: `0`, `""` y `[]` son verdaderos.
Usar `bool()` de Python daría otro resultado para esos valores.

Un `else` pertenece al `if` más cercano que todavía no tiene uno:

```lox
if (true)
    if (false) print "uno";
    else print "dos";
```

Imprime `dos`. El parser consume el `else` al leer el cuerpo del `if` interior.

## while

```lox
var i = 0;
while (i < 3) {
    print i;
    i = i + 1;
}
```

Imprime `0`, `1` y `2`. El AST contiene `WhileStmt(condition, body)`.
`visit_while_stmt()` reevalúa la condición antes de cada vuelta; reutiliza
el árbol, pero lee el valor actualizado de `i`. Si la condición empieza
siendo falsa, no ejecuta el cuerpo.

Un cuerpo con llaves crea un ambiente por vuelta. En el ejemplo, la
asignación de `i` modifica el ambiente exterior.

## for

```lox
for (var i = 0; i < 3; i = i + 1) print i;
```

El parser transforma este `for` en:

```lox
{
    var i = 0;
    while (i < 3) {
        print i;
        i = i + 1;
    }
}
```

Así reutilizamos `BlockStmt`, `WhileStmt` y sus visitantes, sin un nodo
`ForStmt`. El inicializador se ejecuta una vez; el incremento, después de
cada vuelta. El bloque exterior limita el alcance de `i` al bucle.

Se pueden omitir las tres partes del encabezado, conservando los dos `;`.
Sin inicializador o incremento no se agregan esas sentencias; sin condición
se usa `Literal(True)`.

En bytecode, el compilador emite saltos para las ramas y bucles. Rechaza
los desplazamientos mayores a 65535 bytes. Las pruebas de
[test_statements.py](../tests/test_statements.py) cubren ramas, asociación de
`else`, bucles y ámbitos; [test_cli.py](../tests/test_cli.py) cubre los límites
de salto.
