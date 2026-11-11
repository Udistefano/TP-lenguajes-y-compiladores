# Versiones medidas

Cada referencia tiene un JSON con el commit base y los hashes SHA-256, más
un parche que reconstruye `src/` sobre `341d6eb2`. Estos cambios todavía no
estaban en un commit al medirlos.

| Referencia | Estado |
| --- | --- |
| `pre-optimization` | Clases, listas y correcciones de paridad, antes de optimizar la VM |
| `optimized` | VM optimizada; versión de las comparaciones generales |
| `delivery` | Correcciones de paridad y REPL; versión de `results/delivery/`, anterior a los dos arreglos de la revisión final |

`benchmarks/snapshots.py` extrae el commit, aplica el parche y comprueba los
hashes en un directorio temporal. Importa las versiones como paquetes
separados y elimina el directorio al terminar, también si falla la medición.

`compare.py --snapshot benchmarks/baselines/optimized.json` mide esa versión.
Con `--baseline` se la compara contra el checkout actual. El parcial se
reconstruye por separado desde `088a86c2`.
