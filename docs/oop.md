# Clases y herencia

Los dos backends implementan clases y herencia con la sintaxis de Lox.

## Sintaxis

```lox
class Persona {
  init(nombre) { this.nombre = nombre; }
  decir() { return "Soy " + this.nombre; }
}

class Estudiante < Persona {
  init(nombre, carrera) {
    super.init(nombre);
    this.carrera = carrera;
  }
  decir() { return super.decir() + ", estudio " + this.carrera; }
}
```

- Los métodos se declaran sin `fun`.
- `init` es el constructor (se ejecuta al instanciar).
- `this` referencia la instancia actual.
- `super` referencia la superclase (resolución léxica).
- Propiedades con `.`: `obj.prop` y `obj.prop = valor`.
- Los métodos quedan ligados al receptor: `var m = obj.metodo; m();`.

## Backend bytecode

El compilador emite seis instrucciones OOP; otras dos permanecen reservadas:

| Opcode | Operandos | Descripción |
|--------|-----------|-------------|
| `OP_CLASS` | 1 byte (nombre) | Crea una `LoxClass` |
| `OP_GET_PROPERTY` | 1 byte (nombre) | Lee campo o método ligado |
| `OP_SET_PROPERTY` | 1 byte (nombre) | Asigna campo |
| `OP_METHOD` | 1 byte (nombre) | Registra un método en la clase |
| `OP_INHERIT` | 0 bytes | Establece la superclase |
| `OP_GET_SUPER` | 1 byte (nombre) | Resuelve `super.metodo` léxicamente |
| `OP_INVOKE` | 2 bytes (nombre, argc) | Reservado |
| `OP_SUPER_INVOKE` | 2 bytes (nombre, argc) | Reservado |

La resolución de `super` es léxica. Al declarar una subclase, el compilador
guarda la superclase en un local que los métodos capturan como upvalue.
Antes de definir la clase, `OP_INHERIT` retira y valida la superclase de la pila,
dejando la clase nueva debajo. Si falla, conserva el valor anterior del nombre,
incluso cuando está capturado por una función.
`OP_GET_SUPER` recibe esa superclase y el receptor `this` en la pila. Esto
funciona con clases locales, herencia de varios niveles y funciones anidadas
en métodos, aunque cambie la variable que originalmente nombraba la clase.

En tree-walk, el resolver conserva los ámbitos separados de `super`, `this` y
los parámetros. El intérprete usa esas distancias; no busca la clase por su
nombre en el entorno global.

Las instancias y clases se comparan por identidad. Los constructores devuelven
su instancia; en esta implementación se descarta el valor explícito de un
`return` dentro de `init`.

## Verificación

```sh
uv run pytest tests/test_oop.py tests/test_oop_bytecode.py -q
```
