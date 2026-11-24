"""Uso: python -m casos [--notas data/notas.json] [--salida data/casos.json] [--reporte reporte.md]"""

from __future__ import annotations

import argparse
import json
import re
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


_VARIOS = re.compile(r"\bhechos (aislados|distintos|diferentes|separados)\b|\ben otro hecho\b|\buno de los (casos|hechos)\b"
                     r"|\bel otro en\b|\by otr[oa] (result[oó]|qued[oó]|fue)\b", re.I)
_NOMBRE = r"[A-ZÁÉÍÓÚÑ0-9][\wáéíóúñ']*(?: (?:de|del|la|las|los|el|[A-ZÁÉÍÓÚÑ0-9][\wáéíóúñ']*))*"
_DOS_LUGARES = re.compile(rf"\ben (?:el barrio |los barrios )?({_NOMBRE}) y (?:en )?(?:el barrio )?({_NOMBRE})")


def varios_hechos(texto: str, ref: Referencia) -> bool:
    """La nota parece contar más de un hecho: «asesinados en 7 de Abril y El Ferry», «uno de los casos… el otro en…»."""
    if _VARIOS.search(texto):
        return True
    return any(ref.existe(a) and ref.existe(b) and a != b for a, b in _DOS_LUGARES.findall(texto))


def marcar_varios_hechos(casos: list[dict], notas: list[dict], ref: Referencia) -> int:
    """Marca los casos con alguna nota que cuenta varios hechos, para que el editor los separe."""
    por_id = {n["id"]: n for n in notas}
    n = 0
    for c in casos:
        textos = [f"{por_id[i].get('titular', '')}. {por_id[i].get('resumen', '')}" for i in c.get("notas", []) if i in por_id]
        if any(varios_hechos(t, ref) for t in textos):
            c["varios_hechos"] = True
            n += 1
        else:
            c.pop("varios_hechos", None)
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
    ref = Referencia.desde(Path("."))
    deducir_municipio(casos, ref)
    marcar_varios_hechos(casos, notas, ref)
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
