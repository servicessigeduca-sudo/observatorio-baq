from scraper.fuentes import por_id
from scraper.lectores import fecha_desde_texto, leer_listado, leer_nota, leer_rss

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Medio de prueba</title>
<item>
  <title>Sicarios asesinan a hombre en el barrio Las Flores</title>
  <link>https://emisoraatlantico.com.co/judiciales/sicarios-asesinan-hombre/?utm_source=rss</link>
  <pubDate>Wed, 11 Nov 2026 23:22:30 +0000</pubDate>
  <category><![CDATA[Judiciales]]></category>
  <description><![CDATA[<p>Texto de prueba de la entradilla.</p>]]></description>
</item>
<item>
  <title>Festival en Juan de Acosta</title>
  <link>https://emisoraatlantico.com.co/local/festival/</link>
  <pubDate>Wed, 11 Nov 2026 20:00:00 +0000</pubDate>
  <category><![CDATA[Local]]></category>
</item>
</channel></rss>"""


def test_rss_filtra_por_categoria_y_convierte_fecha():
    fuente = por_id(["emisora-atlantico"])[0]
    notas = leer_rss(RSS, fuente)
    assert len(notas) == 1
    n = notas[0]
    assert n["titular"].startswith("Sicarios asesinan")
    assert n["fecha_publicacion"] == "2026-11-11T18:22:30-05:00"
    assert n["resumen"].strip() == "Texto de prueba de la entradilla."


LISTADO = """<html><body>
<a href="/judiciales/mataron-a-hombre-en-la-esmeralda">Mataron a hombre</a>
<a href="/judiciales/mataron-a-hombre-en-la-esmeralda#comentarios">(3)</a>
<a href="https://zonacero.com/judiciales/hieren-mujer-el-valle">Hieren a mujer</a>
<a href="/judiciales?page=1">Ver más</a>
<a href="/politica/concejo">Concejo</a>
</body></html>"""


def test_listado_solo_toma_enlaces_de_notas():
    fuente = por_id(["zona-cero"])[0]
    assert leer_listado(LISTADO, fuente) == [
        "https://zonacero.com/judiciales/mataron-a-hombre-en-la-esmeralda",
        "https://zonacero.com/judiciales/hieren-mujer-el-valle",
    ]


def test_nota_con_metadatos_open_graph():
    html = """<html><head>
    <meta property="og:title" content="Asesinan a vigilante en El Santuario">
    <meta property="og:description" content="Resumen corto.">
    <meta property="article:published_time" content="2026-11-11T08:15:00-05:00">
    </head><body><p>Cuerpo que no se guarda.</p></body></html>"""
    n = leer_nota(html, "https://diariolalibertad.com/2026/11/11/asesinan-vigilante/")
    assert n == {
        "url": "https://diariolalibertad.com/2026/11/11/asesinan-vigilante/",
        "titular": "Asesinan a vigilante en El Santuario",
        "fecha_publicacion": "2026-11-11T08:15:00-05:00",
        "resumen": "Resumen corto.",
    }


def test_nota_con_fecha_visible_estilo_ctv():
    html = "<html><body><h1>Ataque sicarial en Las Estrellas</h1><span>Noticia 14/04/2026, 9:41 p. m.</span></body></html>"
    n = leer_nota(html, "https://ctvbarranquilla.com/article/ataque-sicarial")
    assert n["titular"] == "Ataque sicarial en Las Estrellas"
    assert n["fecha_publicacion"] == "2026-04-14T21:41:00-05:00"


def test_fecha_desde_url():
    assert fecha_desde_texto("https://x.co/2026/11/09/nota/").date().isoformat() == "2026-11-09"


def test_nota_con_jsonld():
    html = """<html><head><script type="application/ld+json">
    {"@context":"https://schema.org","@graph":[{"@type":"NewsArticle","datePublished":"2026-11-10T07:00:00Z"}]}
    </script></head><body><h1>Titular</h1></body></html>"""
    assert leer_nota(html, "https://zonacero.com/judiciales/x")["fecha_publicacion"] == "2026-11-10T02:00:00-05:00"
