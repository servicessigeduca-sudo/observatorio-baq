"""Cliente HTTP respetuoso: robots.txt, pausa por dominio y user-agent propio."""

from __future__ import annotations

import logging
import time
import urllib.robotparser
from urllib.parse import urlsplit

import requests

from . import USER_AGENT

log = logging.getLogger(__name__)


class BloqueadoPorRobots(Exception):
    """La URL está prohibida por el robots.txt del medio."""


class Cliente:
    def __init__(self, sesion: requests.Session | None = None, reloj=time.monotonic, dormir=time.sleep):
        self.sesion = sesion or requests.Session()
        self.sesion.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "es-CO,es;q=0.9"})
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._ultima: dict[str, float] = {}
        self._reloj = reloj
        self._dormir = dormir

    # robots.txt -------------------------------------------------------
    def _parser(self, url: str) -> urllib.robotparser.RobotFileParser:
        partes = urlsplit(url)
        base = f"{partes.scheme}://{partes.netloc}"
        if base not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self.sesion.get(base + "/robots.txt", timeout=20)
                if r.status_code in (401, 403):
                    rp.disallow_all = True
                elif r.status_code >= 400:
                    rp.allow_all = True
                else:
                    rp.parse(r.text.splitlines())
            except requests.RequestException as e:
                # Sin robots.txt legible no seguimos con ese dominio.
                log.warning("No se pudo leer robots.txt de %s: %s", base, e)
                rp.disallow_all = True
            self._robots[base] = rp
        return self._robots[base]

    def permitido(self, url: str) -> bool:
        return self._parser(url).can_fetch(USER_AGENT, url)

    def crawl_delay(self, url: str) -> float:
        d = self._parser(url).crawl_delay(USER_AGENT)
        return float(d) if d else 0.0

    # peticiones -------------------------------------------------------
    def get(self, url: str, pausa: float = 5.0) -> requests.Response:
        if not self.permitido(url):
            raise BloqueadoPorRobots(url)
        dominio = urlsplit(url).netloc
        espera = max(pausa, self.crawl_delay(url))
        ultima = self._ultima.get(dominio)
        if ultima is not None:
            falta = espera - (self._reloj() - ultima)
            if falta > 0:
                self._dormir(falta)
        try:
            r = self.sesion.get(url, timeout=30)
        finally:
            self._ultima[dominio] = self._reloj()
        r.raise_for_status()
        return r
