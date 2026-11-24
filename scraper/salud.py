"""Avisa cuando un medio deja de traer notas.

Si un medio no aporta notas nuevas en `--dias` días (por defecto 3), lo más
probable es que cambió su página o bloqueó el acceso. El flujo Scraper corre
esto después de cada corrida y, si hay medios callados, abre (o actualiza) un
aviso en GitHub para que alguien revise el lector de ese medio.

Uso: python -m scraper.salud [--notas data/notas.json] [--dias 3] [--salida aviso.md]
Sale con código 1 si hay medios sin notas recientes.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

from .fuentes import FUENTES
from .lectores import BOGOTA


def medios_callados(notas: list[dict], ahora: datetime, dias: int = 3) -> list[tuple[str, str | None]]:
    """[(medio, última captura o None)] de los medios sin notas nuevas en `dias` días."""
    ultima: dict[str, str] = {}
    for n in notas:
        if n.get("fecha_captura") and n.get("medio"):
            ultima[n["medio"]] = max(ultima.get(n["medio"], ""), n["fecha_captura"])
    limite = ahora - timedelta(days=dias)
    salida = []
    for f in FUENTES:
        u = ultima.get(f.nombre)
        if u is None or datetime.fromisoformat(u) < limite:
            salida.append((f.nombre, u))
    return salida


def aviso(callados: list[tuple[str, str | None]], dias: int) -> str:
    filas = "\n".join(f"- **{m}**: última nota capturada {('el ' + u[:10]) if u else 'nunca'}" for m, u in callados)
    return (f"Estos medios no traen notas nuevas desde hace más de {dias} días:\n\n{filas}\n\n"
            "Puede que cambiaron su página, su RSS o que bloquearon el acceso. Revisa el resumen de la última corrida "
            "del flujo **Scraper** (pestaña Actions) y el lector de ese medio en `scraper/fuentes.py`.\n\n"
            "Este aviso se actualiza solo en cada corrida y se puede cerrar cuando el medio vuelva a traer notas.\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="scraper.salud")
    ap.add_argument("--notas", default="data/notas.json", type=Path)
    ap.add_argument("--dias", default=3, type=int)
    ap.add_argument("--salida", type=Path, help="escribe el aviso en Markdown en este archivo")
    args = ap.parse_args(argv)
    notas = json.loads(args.notas.read_text(encoding="utf-8")) if args.notas.exists() else []
    callados = medios_callados(notas, datetime.now(BOGOTA), args.dias)
    if not callados:
        print("Todos los medios trajeron notas en los últimos días.")
        return 0
    texto = aviso(callados, args.dias)
    print(texto)
    if args.salida:
        args.salida.write_text(texto, encoding="utf-8")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
