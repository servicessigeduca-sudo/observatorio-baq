"""Medios incluidos en el scraper.

La lista y las razones de cada inclusión o exclusión están en el documento
"Fuentes de noticias del scraper" del proyecto. Excluidos: El Heraldo y
El Tiempo (prohíben el scraping sin permiso escrito), ADN Barranquilla,
La Cháchara y Q'hubo Barranquilla (bloquean el acceso).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Fuente:
    id: str
    nombre: str
    tipo: str  # "rss" o "listado"
    url: str
    prioridad: int
    # Segundos mínimos entre peticiones al mismo dominio.
    pausa: float = 5.0
    # RSS: categorías aceptadas (minúsculas). Vacío = todas.
    categorias: tuple[str, ...] = ()
    # Listado HTML: expresión que deben cumplir los enlaces a notas.
    patron_nota: str = ""
    # Máximo de notas nuevas a abrir por corrida.
    max_notas: int = 30
    # Listado HTML: otras secciones que también se leen, después de `url`.
    urls_extra: tuple[str, ...] = ()
    # Listado HTML: solo abrir enlaces cuyo texto (titular y entradilla del
    # listado) parece una nota judicial. Para secciones generales.
    filtro_judicial: bool = False

    @property
    def listados(self) -> tuple[str, ...]:
        return (self.url, *self.urls_extra)

    def es_nota(self, url: str) -> bool:
        return bool(self.patron_nota) and re.match(self.patron_nota, url) is not None


FUENTES: list[Fuente] = [
    Fuente(
        id="zona-cero",
        nombre="Zona Cero",
        tipo="listado",
        url="https://zonacero.com/judiciales",
        prioridad=1,
        patron_nota=r"^https?://(www\.)?zonacero\.com/judiciales/[^/?#]+/?$",
    ),
    Fuente(
        id="la-libertad",
        nombre="Diario La Libertad",
        tipo="listado",
        url="https://diariolalibertad.com/seccion/cronica-judicial/",
        prioridad=1,
        pausa=10.0,  # Crawl-delay: 10 en su robots.txt
        patron_nota=r"^https?://(www\.)?diariolalibertad\.com/\d{4}/\d{2}/\d{2}/[^/?#]+/?$",
    ),
    Fuente(
        id="emisora-atlantico",
        nombre="Emisora Atlántico",
        tipo="rss",
        url="https://emisoraatlantico.com.co/feed/",
        prioridad=2,
        categorias=("judiciales",),
    ),
    Fuente(
        id="impacto-news",
        nombre="Impacto News",
        tipo="rss",
        url="https://impactonews.co/feed/",
        prioridad=3,
        categorias=("judiciales",),
    ),
    Fuente(
        id="ctv",
        nombre="CTV Barranquilla",
        tipo="listado",
        url="https://ctvbarranquilla.com/category/judiciales",
        # Desde junio de 2026 CTV no marca las notas nuevas como «Judiciales»:
        # salen en Barranquilla y Atlántico junto con el resto de noticias.
        urls_extra=(
            "https://ctvbarranquilla.com/category/barranquilla",
            "https://ctvbarranquilla.com/category/atlantico",
        ),
        filtro_judicial=True,
        prioridad=3,
        patron_nota=r"^https?://(www\.)?ctvbarranquilla\.com/article/[^/?#]+/?$",
    ),
]


def por_id(ids: list[str] | None) -> list[Fuente]:
    if not ids:
        return list(FUENTES)
    desconocidas = set(ids) - {f.id for f in FUENTES}
    if desconocidas:
        raise ValueError(f"Fuentes desconocidas: {', '.join(sorted(desconocidas))}")
    return [f for f in FUENTES if f.id in ids]
