"""Recorre las fuentes y devuelve notas nuevas."""

from __future__ import annotations

import logging
from datetime import datetime

import requests

from .clasificar import clasificar
from .cliente import BloqueadoPorRobots, Cliente
from .fuentes import Fuente
from .lectores import BOGOTA, leer_listado, leer_nota, leer_rss
from .modelo import Nota

log = logging.getLogger(__name__)


def _nota(fuente: Fuente, datos: dict, ahora: str) -> Nota:
    nota = Nota(
        medio=fuente.nombre,
        url=datos["url"],
        titular=datos["titular"],
        fecha_publicacion=datos["fecha_publicacion"],
        resumen=datos.get("resumen", ""),
        fecha_captura=ahora,
    )
    c = clasificar(nota.titular, nota.resumen)
    nota.tipos_delito, nota.municipio, nota.barrio = c["tipos_delito"], c["municipio"], c["barrio"]
    return nota


def recolectar(fuente: Fuente, cliente: Cliente, conocidas: set[str]) -> list[Nota]:
    """`conocidas` son los ids ya guardados: esas notas no se vuelven a abrir."""
    ahora = datetime.now(BOGOTA).isoformat(timespec="seconds")
    try:
        r = cliente.get(fuente.url, pausa=fuente.pausa)
    except BloqueadoPorRobots:
        log.warning("%s: robots.txt no permite %s; se omite", fuente.id, fuente.url)
        return []
    except requests.RequestException as e:
        log.warning("%s: error al leer %s: %s", fuente.id, fuente.url, e)
        return []

    if fuente.tipo == "rss":
        notas = [_nota(fuente, d, ahora) for d in leer_rss(r.content, fuente)]
        return [n for n in notas if n.id not in conocidas]

    notas: list[Nota] = []
    for url in leer_listado(r.text, fuente):
        if len(notas) >= fuente.max_notas:
            break
        candidata = Nota(medio=fuente.nombre, url=url, titular="", fecha_publicacion=None)
        if candidata.id in conocidas:
            continue
        try:
            rn = cliente.get(url, pausa=fuente.pausa)
        except BloqueadoPorRobots:
            continue
        except requests.RequestException as e:
            log.warning("%s: error al leer %s: %s", fuente.id, url, e)
            continue
        notas.append(_nota(fuente, leer_nota(rn.text, url), ahora))
    return notas
