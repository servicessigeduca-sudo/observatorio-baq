"""Un solo criterio para unir nombres de barrio entre prensa, registro y mapa.

`clave()` es la forma comparable de un nombre y debe ser idéntica a
`O.claveBarrio()` en web/datos.js. `Referencia` usa los límites publicados
(data/publico/barrios.geojson) y los alias (data/barrios_alias.json) para:

- dar el nombre oficial de un barrio («Santo Domingo» → «Santo Domingo de Guzman»);
- deducir el municipio cuando el nombre existe en uno solo de los cinco;
- fijar el municipio de barrios que la prensa ubica mal (data/barrios_municipio.json,
  p. ej. El Ferry es de Barranquilla aunque una nota diga Soledad).

No necesita shapely, así que lo pueden usar el scraper, los casos y el sitio.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from scraper.clasificar import normalizar

PREFIJOS = re.compile(r"^(barrio|urbanizacion|urb|conjunto residencial|conjunto|ciudadela|sector|asentamiento)\s+")
NUMEROS = {
    "uno": "1", "primero": "1", "dos": "2", "tres": "3", "cuatro": "4", "cinco": "5", "seis": "6", "siete": "7",
    "ocho": "8", "nueve": "9", "diez": "10", "once": "11", "doce": "12", "trece": "13", "catorce": "14",
    "quince": "15", "veinte": "20",
    "i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10",
}
ARTICULO = re.compile(r"^(el|la|los|las)\s+")


def clave(nombre: str | None) -> str:
    """Sin tildes, signos, «barrio», «urbanización» ni «etapa»; números en cifras («Siete» → 7, «II» → 2)."""
    t = re.sub(r"[^a-z0-9ñ]+", " ", normalizar(nombre or "")).strip()
    t = PREFIJOS.sub("", t)
    pal = [NUMEROS.get(w, w) for w in t.split() if w != "etapa"]
    return " ".join(pal)


def sin_articulo(k: str) -> str:
    return ARTICULO.sub("", k)


class Referencia:
    def __init__(self, geojson: dict | None = None, alias: dict[str, str] | None = None, fijos: dict[str, str] | None = None):
        # barrio -> municipio decidido por el equipo
        self.fijos = {clave(b): m for b, m in (fijos or {}).items()}
        self.geojson, self.alias, self.fijos_nombres = geojson or {}, alias or {}, fijos or {}
        # (municipio, clave) -> nombre oficial
        self._nombre: dict[tuple[str, str], str] = {}
        self._flojo: dict[tuple[str, str], str] = {}  # misma clave sin artículo inicial
        for f in (geojson or {}).get("features", []):
            p = f.get("properties", {})
            m, nombre = p.get("municipio"), p.get("barrio")
            if not m or not nombre:
                continue
            for k in [clave(nombre), *(clave(o) for o in p.get("otros") or [])]:
                self._nombre.setdefault((m, k), nombre)
        for k, v in (alias or {}).items():
            m, dato = k.split("|", 1)
            oficial = self._nombre.get((m, clave(v)))
            if oficial:
                self._nombre.setdefault((m, clave(dato)), oficial)
        for (m, k), nombre in self._nombre.items():
            self._flojo.setdefault((m, sin_articulo(k)), nombre)
        self._municipios: dict[str, set[str]] = defaultdict(set)
        for (m, k) in list(self._nombre) + list(self._flojo):
            self._municipios[k].add(m)

    @classmethod
    def desde(cls, raiz: Path = Path(".")) -> "Referencia":
        leer = lambda p: json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        return cls(leer(raiz / "data" / "publico" / "barrios.geojson"), leer(raiz / "data" / "barrios_alias.json"),
                   leer(raiz / "data" / "barrios_municipio.json"))

    def oficial(self, barrio: str | None, municipio: str | None) -> str | None:
        """Nombre oficial del barrio en ese municipio, o None si no está en la lista."""
        if not barrio or not municipio:
            return None
        k = clave(barrio)
        n = self._nombre.get((municipio, k)) or self._flojo.get((municipio, sin_articulo(k)))
        if n is None and self.fijos.get(k) == municipio:
            n = next(b for b in self.fijos_nombres if clave(b) == k)
        return n

    def codigo(self, barrio: str | None, municipio: str | None) -> str:
        """Código del barrio en la lista única (data/publico/barrios.csv), o "" si no está."""
        from .lista_barrios import codigo
        n = self.oficial(barrio, municipio)
        return codigo(n, municipio) if n else ""

    def lista(self) -> list[dict]:
        from .lista_barrios import filas
        return filas(self.geojson, self.alias, self.fijos_nombres)

    def municipio_unico(self, barrio: str | None) -> str | None:
        """El municipio del barrio si el nombre existe en uno solo; None si no existe o se repite."""
        if not barrio:
            return None
        k = clave(barrio)
        if k in self.fijos:
            return self.fijos[k]
        ms = self._municipios.get(k) or self._municipios.get(sin_articulo(k)) or set()
        return next(iter(ms)) if len(ms) == 1 else None

    def municipio_fijo(self, barrio: str | None) -> str | None:
        """Municipio que el equipo fijó para este barrio, o None."""
        return self.fijos.get(clave(barrio)) if barrio else None

    def existe(self, barrio: str | None) -> bool:
        """True si el nombre está en la lista, en cualquier municipio."""
        if not barrio:
            return False
        k = clave(barrio)
        return k in self.fijos or bool(self._municipios.get(k) or self._municipios.get(sin_articulo(k)))
