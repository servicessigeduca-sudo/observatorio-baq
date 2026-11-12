"""Lectura y escritura de data/notas.json."""

from __future__ import annotations

import json
from pathlib import Path

from .modelo import Nota


def cargar(ruta: Path) -> dict[str, dict]:
    if not ruta.exists():
        return {}
    return {n["id"]: n for n in json.loads(ruta.read_text(encoding="utf-8"))}


def fusionar(existentes: dict[str, dict], nuevas: list[Nota]) -> tuple[dict[str, dict], int]:
    """Agrega las notas nuevas. Nunca pisa una nota ya guardada, porque el
    equipo puede haberla revisado (estado, barrio, tipo)."""
    agregadas = 0
    for n in nuevas:
        if n.id not in existentes:
            existentes[n.id] = n.a_dict()
            agregadas += 1
    return existentes, agregadas


def guardar(ruta: Path, notas: dict[str, dict]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    orden = sorted(notas.values(), key=lambda n: (n.get("fecha_publicacion") or "", n["id"]), reverse=True)
    ruta.write_text(json.dumps(orden, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
