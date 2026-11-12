"""Uso: python -m casos [--notas data/notas.json] [--salida data/casos.json] [--reporte reporte.md]"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agrupar import agrupar
from .reporte import generar


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="casos", description="Agrupa las notas en casos.")
    ap.add_argument("--notas", default="data/notas.json", type=Path)
    ap.add_argument("--salida", default="data/casos.json", type=Path)
    ap.add_argument("--reporte", type=Path, help="escribe el resumen en Markdown en este archivo")
    args = ap.parse_args(argv)

    notas = json.loads(args.notas.read_text(encoding="utf-8")) if args.notas.exists() else []
    previos = json.loads(args.salida.read_text(encoding="utf-8")) if args.salida.exists() else []
    casos = agrupar(notas, previos)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(casos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    texto = generar(notas, casos)
    if args.reporte:
        args.reporte.write_text(texto, encoding="utf-8")
    print(texto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
