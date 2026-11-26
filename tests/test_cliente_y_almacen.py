import json

import pytest

from scraper import almacen
from scraper.cliente import BloqueadoPorRobots, Cliente
from scraper.fuentes import por_id
from scraper.modelo import Nota, recortar
from scraper.recolector import recolectar


class Resp:
    def __init__(self, texto, status=200):
        self.text = texto
        self.content = texto.encode()
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(self.status_code)


class SesionFalsa:
    def __init__(self, paginas):
        self.paginas = paginas
        self.headers = {}
        self.pedidas = []

    def get(self, url, timeout=None):
        self.pedidas.append(url)
        return self.paginas.get(url, Resp("", 404))


class Reloj:
    def __init__(self):
        self.t = 0.0
        self.esperas = []

    def ahora(self):
        return self.t

    def dormir(self, s):
        self.esperas.append(s)
        self.t += s


def cliente(paginas):
    r = Reloj()
    return Cliente(SesionFalsa(paginas), reloj=r.ahora, dormir=r.dormir), r


def test_respeta_robots_disallow():
    c, _ = cliente({"https://a.co/robots.txt": Resp("User-agent: *\nDisallow: /privado/\n")})
    with pytest.raises(BloqueadoPorRobots):
        c.get("https://a.co/privado/x")


def test_bots_de_ia_bloqueados_no_afectan_nuestro_user_agent():
    robots = "User-agent: ClaudeBot\nDisallow: /\n\nUser-agent: *\nAllow: /\nCrawl-delay: 10\n"
    c, reloj = cliente({"https://b.co/robots.txt": Resp(robots), "https://b.co/1": Resp("uno"), "https://b.co/2": Resp("dos")})
    assert c.get("https://b.co/1", pausa=5).text == "uno"
    c.get("https://b.co/2", pausa=5)
    # usa el Crawl-delay (10 s) porque es mayor que la pausa (5 s)
    assert reloj.esperas == [10.0]


def test_robots_403_bloquea_todo():
    c, _ = cliente({"https://c.co/robots.txt": Resp("", 403)})
    assert not c.permitido("https://c.co/")


def test_recortar_resumen():
    largo = "palabra " * 100
    r = recortar(largo)
    assert len(r) <= 300 and r.endswith("…")


def test_mismo_id_con_y_sin_www_ni_barra():
    a = Nota(medio="m", url="https://www.zonacero.com/judiciales/x/", titular="t", fecha_publicacion=None)
    b = Nota(medio="m", url="https://zonacero.com/judiciales/x?utm_source=fb", titular="t", fecha_publicacion=None)
    assert a.id == b.id


def test_fusionar_no_pisa_notas_revisadas(tmp_path):
    ruta = tmp_path / "notas.json"
    n = Nota(medio="m", url="https://x.co/a", titular="t", fecha_publicacion="2026-11-11T00:00:00-05:00")
    revisada = n.a_dict() | {"estado": "verificado", "barrio": "Rebolo"}
    ruta.write_text(json.dumps([revisada]))
    existentes, agregadas = almacen.fusionar(almacen.cargar(ruta), [n])
    assert agregadas == 0
    assert existentes[n.id]["estado"] == "verificado"


def test_recolectar_listado_abre_solo_notas_nuevas():
    fuente = por_id(["zona-cero"])[0]
    listado = '<a href="/judiciales/nota-vieja">v</a><a href="/judiciales/nota-nueva">n</a>'
    nota = '<meta property="og:title" content="Asesinan a hombre en el barrio Rebolo"><meta property="article:published_time" content="2026-11-11T10:00:00-05:00">'
    paginas = {
        "https://zonacero.com/robots.txt": Resp("User-agent: *\nDisallow: /admin/\n"),
        "https://zonacero.com/judiciales": Resp(listado),
        "https://zonacero.com/judiciales/nota-nueva": Resp(nota),
    }
    c, _ = cliente(paginas)
    vieja = Nota(medio="Zona Cero", url="https://zonacero.com/judiciales/nota-vieja", titular="", fecha_publicacion=None)
    notas = recolectar(fuente, c, {vieja.id})
    assert [n.titular for n in notas] == ["Asesinan a hombre en el barrio Rebolo"]
    assert notas[0].tipos_delito == ["homicidio"] and notas[0].barrio == "Rebolo"
    assert "https://zonacero.com/judiciales/nota-vieja" not in c.sesion.pedidas


def test_ctv_lee_varias_secciones_y_solo_abre_notas_judiciales():
    fuente = por_id(["ctv"])[0]
    base = "https://ctvbarranquilla.com"
    nota = (
        '<meta property="og:title" content="Disparan contra vivienda de una funcionaria del INPEC">'
        '<meta property="article:published_time" content="2026-11-25T11:12:00-05:00">'
    )
    paginas = {
        base + "/robots.txt": Resp("User-agent: *\nAllow: /\n"),
        # La sección Judiciales quedó congelada: solo trae notas ya guardadas.
        base + "/category/judiciales": Resp('<a href="/article/nota-vieja">Asesinan a hombre</a>'),
        base + "/category/barranquilla": Resp(
            '<a href="/article/disparan-contra-vivienda"><img alt="">Barranquilla '
            "Disparan contra vivienda de una funcionaria del INPEC Un ataque armado</a>"
            '<a href="/article/avianca-ruta">Barranquilla Avianca abre ruta a Nueva York</a>'
        ),
        base + "/category/atlantico": Resp(
            '<a href="/article/sicario-persiguio">Sicario persiguió a dos hombres y los asesinó a bala</a>'
            '<a href="/article/disparan-contra-vivienda">repetida</a>'
        ),
        base + "/article/disparan-contra-vivienda": Resp(nota),
        base + "/article/sicario-persiguio": Resp(nota),
    }
    c, _ = cliente(paginas)
    vieja = Nota(medio=fuente.nombre, url=base + "/article/nota-vieja", titular="", fecha_publicacion=None)
    notas = recolectar(fuente, c, {vieja.id})
    assert [n.url for n in notas] == [base + "/article/disparan-contra-vivienda", base + "/article/sicario-persiguio"]
    assert base + "/article/avianca-ruta" not in c.sesion.pedidas
    assert base + "/article/nota-vieja" not in c.sesion.pedidas


def test_una_seccion_caida_no_tumba_las_demas():
    fuente = por_id(["ctv"])[0]
    base = "https://ctvbarranquilla.com"
    paginas = {
        base + "/robots.txt": Resp("User-agent: *\nAllow: /\n"),
        base + "/category/atlantico": Resp('<a href="/article/asesinan-hombre">Asesinan a hombre en Soledad</a>'),
        base + "/article/asesinan-hombre": Resp('<meta property="og:title" content="Asesinan a hombre en Soledad">'),
    }
    c, _ = cliente(paginas)
    notas = recolectar(fuente, c, set())
    assert [n.titular for n in notas] == ["Asesinan a hombre en Soledad"]
