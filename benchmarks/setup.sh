#!/usr/bin/env bash
# setup.sh — prepara las implementaciones externas del benchmark.
#
# Descarga (shallow) el repositorio del libro Crafting Interpreters y compila
# los harness de jlox y clox dentro de benchmarks/.cache/, que está ignorado
# por git. mylox y plox no necesitan nada: se importan directamente.
#
# Uso: benchmarks/setup.sh
# Variables opcionales:
#   CI_REPO_URL   URL del repositorio (por defecto el oficial del libro).
#   CI_REF        Rama o tag a descargar (por defecto: master).

set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE="$AQUI/.cache"
REPO="$CACHE/craftinginterpreters"
HARNESS="$AQUI/harness"

CI_REPO_URL="${CI_REPO_URL:-https://github.com/munificent/craftinginterpreters.git}"
CI_REF="${CI_REF:-master}"

mkdir -p "$CACHE"

if [ ! -d "$REPO/.git" ]; then
  echo "[setup] clonando $CI_REPO_URL ($CI_REF)..."
  git clone --depth 1 --branch "$CI_REF" "$CI_REPO_URL" "$REPO"
else
  echo "[setup] el repositorio ya está en $REPO"
fi

# --- jlox: se compila todo el package junto al harness ---
if command -v javac >/dev/null 2>&1; then
  echo "[setup] compilando jlox..."
  rm -rf "$CACHE/jlox-build"
  mkdir -p "$CACHE/jlox-build"
  javac -d "$CACHE/jlox-build" \
    "$REPO/java/com/craftinginterpreters/lox/"*.java \
    "$HARNESS/jlox/Bench.java"
  echo "[setup] jlox listo en $CACHE/jlox-build"
else
  echo "[setup] javac no está disponible: se omite jlox" >&2
fi

# --- clox: el harness reemplaza a main.c (que es la CLI) ---
if command -v gcc >/dev/null 2>&1; then
  echo "[setup] compilando clox..."
  C_DIR="$REPO/c"
  gcc -std=c99 -O2 -I"$C_DIR" -o "$CACHE/cloxbench" \
    "$HARNESS/clox/cloxbench.c" \
    "$C_DIR/vm.c" "$C_DIR/compiler.c" "$C_DIR/chunk.c" "$C_DIR/memory.c" \
    "$C_DIR/object.c" "$C_DIR/scanner.c" "$C_DIR/table.c" "$C_DIR/value.c" \
    "$C_DIR/debug.c" -lm
  echo "[setup] clox listo en $CACHE/cloxbench"
else
  echo "[setup] gcc no está disponible: se omite clox" >&2
fi

echo "[setup] listo. correr: uv run python benchmarks/bench.py"
