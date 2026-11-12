"""Uso: python -m scraper [--fuentes zona-cero,la-libertad] [--salida data/notas.json]"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from . import almacen
from .cliente import Cliente
from .fuentes import por_id
from .recolector import recolectar


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="scraper", description="Recolecta notas judiciales de medios de Barranquilla.")
    ap.add_argument("--fuentes", help="ids separados por coma (por defecto, todas)")
    ap.add_argument("--salida", default="data/notas.json", type=Path)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s")

    fuentes = por_id(args.fuentes.split(",") if args.fuentes else None)
    existentes = almacen.cargar(args.salida)
    cliente = Cliente()
    total = 0
    for f in sorted(fuentes, key=lambda f: f.prioridad):
        nuevas = recolectar(f, cliente, set(existentes))
        existentes, n = almacen.fusionar(existentes, nuevas)
        total += n
        print(f"{f.nombre}: {n} notas nuevas")
    almacen.guardar(args.salida, existentes)
    print(f"Total: {total} notas nuevas, {len(existentes)} guardadas en {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
