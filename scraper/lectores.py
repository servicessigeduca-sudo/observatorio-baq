"""Lectura de RSS, listados de sección y metadatos de una nota.

De cada página se leen solo metadatos (og:title, og:description,
article:published_time, fecha visible). El cuerpo no se guarda.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import feedparser
from bs4 import BeautifulSoup

from .fuentes import Fuente
from .modelo import clave_url

BOGOTA = timezone(timedelta(hours=-5))


# fechas ---------------------------------------------------------------
def a_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BOGOTA)
    return dt.astimezone(BOGOTA).isoformat(timespec="seconds")


def fecha_desde_texto(texto: str | None) -> datetime | None:
    """Acepta ISO 8601, 'DD/MM/AAAA[, h:mm a. m.]' y fechas en la URL."""
    if not texto:
        return None
    texto = texto.strip()
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        pass
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})(?:[,\s]+(\d{1,2}):(\d{2})\s*([ap])\.?\s*m\.?)?", texto, re.I)
    if m:
        d, mes, a = int(m[1]), int(m[2]), int(m[3])
        h, mi = (int(m[4]), int(m[5])) if m[4] else (0, 0)
        if m[6]:
            if m[6].lower() == "p" and h < 12:
                h += 12
            if m[6].lower() == "a" and h == 12:
                h = 0
        try:
            return datetime(a, mes, d, h, mi, tzinfo=BOGOTA)
        except ValueError:
            return None
    m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", texto)
    if m:
        try:
            return datetime(int(m[1]), int(m[2]), int(m[3]), tzinfo=BOGOTA)
        except ValueError:
            return None
    return None


# RSS ------------------------------------------------------------------
def leer_rss(xml: bytes | str, fuente: Fuente) -> list[dict]:
    feed = feedparser.parse(xml)
    salida = []
    for e in feed.entries:
        cats = {t.get("term", "").strip().lower() for t in e.get("tags", [])}
        if fuente.categorias and not cats & set(fuente.categorias):
            continue
        fecha = None
        if e.get("published_parsed"):
            fecha = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
        resumen = BeautifulSoup(e.get("summary", ""), "html.parser").get_text(" ")
        salida.append(
            {
                "url": e.get("link", ""),
                "titular": e.get("title", ""),
                "fecha_publicacion": a_iso(fecha),
                "resumen": resumen,
            }
        )
    return salida


# listado de sección ---------------------------------------------------
def leer_listado(html: str, fuente: Fuente) -> list[str]:
    """Devuelve las URLs de notas del listado, en orden y sin repetir."""
    soup = BeautifulSoup(html, "html.parser")
    vistas: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        # Algunos medios dejan espacios en el href (Zona Cero: "/judiciales/x ").
        url = urljoin(fuente.url, a["href"].strip()).split("#")[0].split("?")[0]
        if fuente.es_nota(url):
            vistas.setdefault(clave_url(url), url)
    return list(vistas.values())


# metadatos de una nota ------------------------------------------------
def _meta(soup: BeautifulSoup, *nombres: str) -> str | None:
    for n in nombres:
        tag = soup.find("meta", attrs={"property": n}) or soup.find("meta", attrs={"name": n})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return None


def _jsonld_fecha(soup: BeautifulSoup) -> str | None:
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            datos = json.loads(s.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        pila = datos if isinstance(datos, list) else [datos]
        while pila:
            d = pila.pop()
            if isinstance(d, dict):
                if d.get("datePublished"):
                    return d["datePublished"]
                pila.extend(d.get("@graph", []))
    return None


def leer_nota(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    titular = _meta(soup, "og:title", "twitter:title")
    if not titular and soup.find("h1"):
        titular = soup.find("h1").get_text(" ", strip=True)
    if not titular and soup.title:
        titular = soup.title.get_text(strip=True)

    fecha = fecha_desde_texto(_meta(soup, "article:published_time", "datePublished") or _jsonld_fecha(soup))
    if fecha is None and soup.find("time", datetime=True):
        fecha = fecha_desde_texto(soup.find("time", datetime=True)["datetime"])
    if fecha is None:
        fecha = fecha_desde_texto(url)
    if fecha is None:
        # Fecha visible (p. ej. CTV: "Noticia 14/04/2026, 9:41 a. m.").
        m = re.search(r"\d{1,2}/\d{1,2}/\d{4}(?:,\s*\d{1,2}:\d{2}\s*[ap]\.?\s*m\.?)?", soup.get_text(" "), re.I)
        if m:
            fecha = fecha_desde_texto(m[0])

    return {
        "url": url,
        "titular": titular or "",
        "fecha_publicacion": a_iso(fecha),
        "resumen": _meta(soup, "og:description", "description", "twitter:description") or "",
    }
