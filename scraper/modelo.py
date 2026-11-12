from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from urllib.parse import urlsplit, urlunsplit

MAX_RESUMEN = 300


def limpiar_url(url: str) -> str:
    """Quita parámetros de seguimiento y fragmentos."""
    p = urlsplit(url.strip())
    return urlunsplit((p.scheme, p.netloc, p.path, "", ""))


def clave_url(url: str) -> str:
    """Forma normalizada para detectar la misma nota con URLs distintas."""
    p = urlsplit(url.strip())
    ruta = p.path.rstrip("/") or "/"
    return f"{p.netloc.lower().removeprefix('www.')}{ruta}"


def recortar(texto: str | None, maximo: int = MAX_RESUMEN) -> str:
    if not texto:
        return ""
    texto = " ".join(texto.split())
    if len(texto) <= maximo:
        return texto
    corte = texto[: maximo - 1].rsplit(" ", 1)[0]
    return corte + "…"


@dataclass
class Nota:
    medio: str
    url: str
    titular: str
    fecha_publicacion: str | None
    resumen: str = ""
    fecha_captura: str = ""
    tipos_delito: list[str] = field(default_factory=list)
    municipio: str | None = None
    barrio: str | None = None
    estado: str = "pendiente"
    id: str = ""

    def __post_init__(self):
        self.url = limpiar_url(self.url)
        self.resumen = recortar(self.resumen)
        self.titular = " ".join(self.titular.split())
        if not self.id:
            self.id = hashlib.sha1(clave_url(self.url).encode()).hexdigest()

    def a_dict(self) -> dict:
        return asdict(self)
