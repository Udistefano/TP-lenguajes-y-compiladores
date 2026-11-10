# Programación orientada a objetos en mylox

mylox implementa OOP (clases + herencia) en **ambos backends** (tree-walk y bytecode),
con la misma sintaxis de Lox.

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

- Métodos se declaran **sin** `fun`.
- `init` es el constructor (se ejecuta al instanciar).
- `this` referencia la instancia actual.
- `super` referencia la superclase (resolución léxica).
- Propiedades con `.`: `obj.prop` y `obj.prop = valor`.
- Métodos son "bound": `var m = obj.metodo; m();` funciona.

## Backend bytecode

El compilador emite 8 opcodes OOP propios (no copiados de clox/ploxb):

| Opcode | Operandos | Descripción |
|--------|-----------|-------------|
| `OP_CLASS` | 1 byte (nombre) | Crea una `LoxClass` |
| `OP_GET_PROPERTY` | 1 byte (nombre) | Lee campo o método ligado |
| `OP_SET_PROPERTY` | 1 byte (nombre) | Asigna campo |
| `OP_METHOD` | 1 byte (nombre) | Registra un método en la clase |
| `OP_INHERIT` | 0 bytes | Establece la superclase |
| `OP_GET_SUPER` | 1 byte (nombre) | Resuelve `super.metodo` lexicamente |
| `OP_INVOKE` | 2 bytes (nombre, argc) | (reservado, no emitido aún) |
| `OP_SUPER_INVOKE` | 2 bytes (nombre, argc) | (reservado, no emitido aún) |

La resolución de `super` es léxica: se usa la clase donde el método está
definido (`enclosing_class`), no la clase runtime de la instancia. Esto
permite herencia de múltiples niveles correctamente.

## Verificación

```sh
# Ambos backends deben dar la misma salida
uv run mylox programa.lox --backend tree-walk
uv run mylox programa.lox --backend bytecode

# Tests
uv run pytest tests/test_oop.py tests/test_oop_bytecode.py -q
```
