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
    if fuente.tipo == "rss":
        r = _leer(fuente, fuente.url, cliente)
        if r is None:
            return []
        notas = [_nota(fuente, d, ahora) for d in leer_rss(r.content, fuente)]
        return [n for n in notas if n.id not in conocidas]

    # Listado: se juntan las secciones en orden, sin repetir notas.
    urls: dict[str, str] = {}
    for listado in fuente.listados:
        r = _leer(fuente, listado, cliente)
        if r is None:
            continue
        for url in leer_listado(r.text, fuente):
            candidata = Nota(medio=fuente.nombre, url=url, titular="", fecha_publicacion=None)
            urls.setdefault(candidata.id, url)

    notas: list[Nota] = []
    for id_, url in urls.items():
        if len(notas) >= fuente.max_notas:
            break
        if id_ in conocidas:
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


def _leer(fuente: Fuente, url: str, cliente: Cliente) -> requests.Response | None:
    try:
        return cliente.get(url, pausa=fuente.pausa)
    except BloqueadoPorRobots:
        log.warning("%s: robots.txt no permite %s; se omite", fuente.id, url)
    except requests.RequestException as e:
        log.warning("%s: error al leer %s: %s", fuente.id, url, e)
    return None
