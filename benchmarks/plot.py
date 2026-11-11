from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

LABELS = {
    "bytecode-before": "VM antes",
    "bytecode-after": "VM optimizada",
    "tree-walk": "Tree-walk actual",
    "partial": "Tree-walk del parcial",
    "plox": "plox (Python)",
    "clox": "clox (C)",
    "python-native": "Python directo",
    "javascript-native": "JavaScript directo",
}
COLORS = {
    "bytecode-before": "#8290a0",
    "bytecode-after": "#007f80",
    "tree-walk": "#4866ae",
    "partial": "#b38a3d",
    "plox": "#b45c81",
    "clox": "#62a05a",
    "python-native": "#4866ae",
    "javascript-native": "#be7628",
}


def summarize(result):
    groups = {}
    for sample in result["samples"]:
        groups.setdefault((sample["program"], sample["variant"]), []).append(sample)
    rows = []
    for (program, variant), samples in groups.items():
        if len(samples) != result["repetitions"]:
            raise ValueError(f"Faltan muestras: {program}/{variant}")
        times = [sample["total_ms"] for sample in samples]
        q25, median, q75 = np.percentile(times, [25, 50, 75])
        row = {
            "program": program, "variant": variant, "n": len(times),
            "median_ms": float(median), "q25_ms": float(q25), "q75_ms": float(q75),
            "min_ms": min(times), "max_ms": max(times),
        }
        for field in ("frontend_ms", "execution_ms"):
            row[field] = float(np.median([s[field] for s in samples])) if field in samples[0] else None
        rows.append(row)
    return rows


def write_csv(path, rows):
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def bars(ax, programs, variants, summary, logarithmic=False):
    positions = np.arange(len(programs))
    width = 0.8 / len(variants)
    for i, variant in enumerate(variants):
        rows = [summary[program, variant] for program in programs]
        medians = np.array([row["median_ms"] for row in rows])
        errors = [medians - [row["q25_ms"] for row in rows], [row["q75_ms"] for row in rows] - medians]
        ax.bar(positions + (i - (len(variants) - 1) / 2) * width, medians, width,
               color=COLORS[variant], label=LABELS[variant], yerr=errors,
               capsize=2, error_kw={"elinewidth": 1})
    ax.set_xticks(positions, programs)
    ax.set_ylabel("Tiempo total (ms)" + (" · escala logarítmica" if logarithmic else ""))
    if logarithmic:
        ax.set_yscale("log")
    ax.grid(axis="y", alpha=0.18)
    ax.set_axisbelow(True)


def export(fig, directory, name, note):
    fig.text(0.01, 0.015, note, fontsize=9, color="#495365")
    fig.tight_layout(rect=(0, 0.055, 1, 1))
    for extension in ("svg", "png"):
        fig.savefig(directory / f"{name}.{extension}", dpi=180, facecolor="white")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/graphs"))
    parser.add_argument("--control", type=Path)
    parser.add_argument("--only-vm", action="store_true")
    args = parser.parse_args()
    if args.only_vm:
        LABELS["bytecode-after"] = "VM después"
    result = json.loads(args.results.read_text(encoding="utf-8"))
    if not result.get("complete") or (not args.only_vm and not result.get("external_complete")):
        parser.error("La comparación debe estar completa, incluidas las referencias externas")
    args.output.mkdir(parents=True, exist_ok=True)
    rows = summarize(result)
    summary = {(row["program"], row["variant"]): row for row in rows}
    write_csv(args.results.with_name("summary.csv"), rows)
    write_csv(args.results.with_name("samples.csv"), result["samples"])
    programs = list(result["programs"])
    portable = [name for name in programs if name not in ("objetos", "listas")]
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    environment = result["machine"]
    cpu = environment["cpu"].removesuffix(" 8-Core Processor")
    system = "WSL2" if "wsl2" in environment["platform"].lower() else environment["platform"].split("-")[0]
    python = environment["python"].split()[0]
    note = (f"Mediana e intervalo intercuartílico · {result['repetitions']} muestras + "
            f"{result['warmup']} de calentamiento · {cpu} · {system} · CPython {python}")

    fig, ax = plt.subplots(figsize=(10, 6.4))
    positions = np.arange(len(programs))
    for offset, variant in ((-0.18, "bytecode-before"), (0.18, "bytecode-after")):
        data = [summary[name, variant] for name in programs]
        medians = np.array([row["median_ms"] for row in data])
        errors = [medians - [row["q25_ms"] for row in data], [row["q75_ms"] for row in data] - medians]
        ax.barh(positions + offset, medians, height=0.32, xerr=errors, capsize=3,
                label=LABELS[variant], color=COLORS[variant])
    for i, name in enumerate(programs):
        before = summary[name, "bytecode-before"]["median_ms"]
        after = summary[name, "bytecode-after"]["median_ms"]
        right = max(summary[name, variant]["q75_ms"] for variant in ("bytecode-before", "bytecode-after"))
        ax.annotate(f"{100 * (after / before - 1):+.1f}%", (right, i),
                    xytext=(9, 0), textcoords="offset points", va="center", fontweight="bold")
    ax.set_yticks(positions, programs)
    ax.invert_yaxis()
    ax.set_xlim(0, ax.get_xlim()[1] * 1.12)
    ax.set_xlabel("Tiempo total (ms) · menor es mejor")
    ax.set_title("Bytecode antes y después", loc="left", fontsize=17, pad=18)
    ax.grid(axis="x", alpha=0.18)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", frameon=False)
    export(fig, args.output, "bytecode-before-after", note + "\nPorcentajes: variación del tiempo mediano; incluyen compilación y ejecución.")

    if args.control:
        control = json.loads(args.control.read_text(encoding="utf-8"))
        if not control["complete"]:
            parser.error("La corrida de control no está completa")
        for key in ("machine", "repetitions", "warmup", "baseline_patch_sha256", "current_sources_sha256"):
            if control[key] != result[key]:
                parser.error(f"La corrida de control difiere en {key}")
        if args.control.resolve() != args.results.resolve():
            write_csv(args.control.with_name("control-samples.csv"), control["samples"])
        cpu_result = {**control, "samples": [
            {"program": s["program"], "variant": s["variant"], "round": s["round"], "total_ms": s["cpu_ms"]}
            for s in control["samples"]
        ]}
        cpu_rows = summarize(cpu_result)
        write_csv(args.control.with_name("control-cpu-summary.csv"), cpu_rows)
        cpu_summary = {(row["program"], row["variant"]): row for row in cpu_rows}
        fig, ax = plt.subplots(figsize=(11, 5.8))
        bars(ax, programs, ["bytecode-before", "bytecode-after"], cpu_summary)
        for i, name in enumerate(programs):
            before = cpu_summary[name, "bytecode-before"]["median_ms"]
            after = cpu_summary[name, "bytecode-after"]["median_ms"]
            top = max(cpu_summary[name, variant]["q75_ms"] for variant in ("bytecode-before", "bytecode-after"))
            ax.annotate(f"{100 * (after / before - 1):+.1f}%", (i, top),
                        xytext=(0, 8), textcoords="offset points", ha="center", fontsize=10)
        ax.set_ylim(0, ax.get_ylim()[1] * 1.1)
        ax.set_ylabel("Tiempo de CPU (ms) · menor es mejor")
        ax.set_title("Comparación con tiempo de CPU", loc="left", fontsize=16, pad=18)
        ax.legend(frameon=False)
        export(fig, args.output, "bytecode-cpu", note + "\nprocess_time_ns incluye preparación y ejecución; excluye el tiempo sin ejecutar en CPU.")

    if args.only_vm:
        print(f"Comparación de VM en {args.output}")
        return

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6), gridspec_kw={"width_ratios": [5, 2]}, sharey=True)
    bars(axes[0], portable, ["partial", "tree-walk", "bytecode-after"], summary)
    bars(axes[1], ["objetos", "listas"], ["tree-walk", "bytecode-after"], summary)
    axes[0].set_title("Del parcial a la entrega final", loc="left", fontsize=16, pad=45)
    axes[1].set_title("Extensiones de la final", loc="left", fontsize=14, pad=18)
    axes[1].set_ylabel("")
    axes[0].legend(frameon=False, fontsize=9, ncol=3, loc="lower left", bbox_to_anchor=(0, 1.01))
    export(fig, args.output, "evolution", note + "\nEl parcial (088a86c) se volvió a medir en el mismo entorno; no implementa clases ni listas.")

    fig, ax = plt.subplots(figsize=(11, 5.8))
    bars(ax, portable, ["plox", "tree-walk", "bytecode-after", "clox"], summary, logarithmic=True)
    ax.set_title("Un mismo lenguaje: cuatro implementaciones de Lox", loc="left", fontsize=16, pad=45)
    ax.legend(ncol=4, frameon=False, loc="lower left", bbox_to_anchor=(0, 1.01), fontsize=10)
    compiler = result["clox"]["compiler"].split()[-1]
    flags = " ".join(result["clox"]["flags"])
    export(fig, args.output, "lox-implementations", note + f"\nclox: GCC {compiler}, {flags}. Cambian el runtime anfitrión y la implementación.")

    fig, ax = plt.subplots(figsize=(11, 5.8))
    bars(ax, portable, ["bytecode-after", "python-native", "javascript-native"], summary, logarithmic=True)
    ax.set_title("El mismo algoritmo escrito en distintos lenguajes", loc="left", fontsize=16, pad=45)
    ax.legend(ncol=3, frameon=False, loc="lower left", bbox_to_anchor=(0, 1.01), fontsize=10)
    node = result["javascript"]["node"]
    export(fig, args.output, "native-languages", note + f"\nMismos límites y algoritmos; Python {python} y Node {node} / V8. Sin arranque de procesos.")
    print(f"Gráficos SVG/PNG en {args.output}; tablas CSV en {args.results.parent}")


if __name__ == "__main__":
    main()
