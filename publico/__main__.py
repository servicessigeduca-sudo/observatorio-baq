"""Uso:
    python -m publico                         # arma data/publico/ desde los datos internos
    python -m publico --capa ruta/query.json  # además agrega la capa de homicidios (el archivo no se copia)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .construir import construir
from .registro import leer, procesar


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="publico", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".", type=Path)
    ap.add_argument("--capa", type=Path, help="GeoJSON de la capa de homicidios (queda fuera del repositorio)")
    args = ap.parse_args(argv)
    if args.capa:
        reg = procesar(leer(args.capa))
        destino = args.raiz / "data" / "publico"
        destino.mkdir(parents=True, exist_ok=True)
        (destino / "registro.json").write_text(json.dumps(reg, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        print(f"Registro: {reg['calidad']['en_el_area']} homicidios en el área, corte {reg['corte']}, {len(reg['zonas'])} zonas")
    res = construir(args.raiz)
    s = res["semana"]
    print(f"Semana {s['desde']} a {s['hasta']}: {s['casos']} casos de prensa (anterior: {s['anterior']['casos']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
