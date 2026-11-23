"""Uso: python -m casos [--notas data/notas.json] [--salida data/casos.json] [--reporte reporte.md]"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from publico.nombres_barrio import Referencia

from .agrupar import agrupar
from .geocodificar import geocodificar
from .reporte import generar


def deducir_municipio(casos: list[dict], ref: Referencia) -> int:
    """Si un caso no trae municipio y su barrio existe en uno solo de los cinco, toma ese.
    Si el nombre se repite en varios municipios (Villa María, La Victoria), no se adivina.
    Los barrios de data/barrios_municipio.json toman siempre ese municipio, salvo en casos ya revisados."""
    n = 0
    for c in casos:
        fijo = ref.municipio_fijo(c.get("barrio"))
        if fijo and c.get("municipio") != fijo and c.get("estado") not in ("publicado", "descartado"):
            c["municipio"], c["municipio_deducido"] = fijo, True
            n += 1
            continue
        if c.get("municipio") or not c.get("barrio"):
            continue
        m = ref.municipio_unico(c["barrio"])
        if m:
            c["municipio"], c["municipio_deducido"] = m, True
            n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="casos", description="Agrupa las notas en casos.")
    ap.add_argument("--notas", default="data/notas.json", type=Path)
    ap.add_argument("--salida", default="data/casos.json", type=Path)
    ap.add_argument("--reporte", type=Path, help="escribe el resumen en Markdown en este archivo")
    ap.add_argument("--geocodificar", action="store_true", help="ubica los barrios con Nominatim (usa data/geocodigos.json)")
    ap.add_argument("--geocodigos", default="data/geocodigos.json", type=Path)
    args = ap.parse_args(argv)

    notas = json.loads(args.notas.read_text(encoding="utf-8")) if args.notas.exists() else []
    previos = json.loads(args.salida.read_text(encoding="utf-8")) if args.salida.exists() else []
    casos = agrupar(notas, previos)
    deducir_municipio(casos, Referencia.desde(Path(".")))
    geocodificar(casos, args.geocodigos, consultar_red=args.geocodificar)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(casos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    texto = generar(notas, casos)
    if args.reporte:
        args.reporte.write_text(texto, encoding="utf-8")
    print(texto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
