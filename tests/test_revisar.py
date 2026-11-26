"""Lógica del panel de revisión (web/revisar.js), corrida con node."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scraper.clasificar import es_captura_o_judicial

JS = Path(__file__).resolve().parents[1] / "web" / "revisar.js"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="sin node")


def correr(codigo: str):
    js = f"require({json.dumps(str(JS))});const RV=globalThis.RV;console.log(JSON.stringify((()=>{{{codigo}}})()))"
    return json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)


NOTAS = {
    "n1": {"url": "https://a.co/1", "fecha_publicacion": "2026-11-10T08:00:00-05:00", "tipos_delito": ["homicidio"], "barrio": "Rebolo", "municipio": "Barranquilla"},
    "n2": {"url": "https://b.co/2", "fecha_publicacion": "2026-11-11T08:00:00-05:00", "tipos_delito": ["captura", "hurto_motos"], "barrio": "La Luz", "municipio": "Barranquilla"},
}
CASO = {"caso_id": "x", "tipo": "homicidio", "tipos": ["homicidio"], "fecha": "2026-11-10", "municipio": "Barranquilla",
        "barrio": "Rebolo", "medios": ["a", "b"], "notas": ["n1", "n2"], "estado": "publicado", "revisado_por": "ed",
        "fuentes": [{"medio": "a", "url": "https://a.co/1", "titular": "Asesinan a hombre"},
                    {"medio": "b", "url": "https://b.co/2", "titular": "Roban moto"}], "posible_duplicado_de": []}


def test_separar_un_enlace_crea_un_caso_aparte():
    r = correr(f"return RV.aplicar([{json.dumps(CASO)}], {{x:{{separar:['n2']}}}}, 'yo', '2026-11-24', {json.dumps(NOTAS)})")
    assert r["aplicados"] == 1
    viejo, nuevo = r["casos"]
    assert viejo["notas"] == ["n1"] and viejo["medios"] == ["a"] and viejo["no_unir_con"] == ["n2"]
    assert viejo["estado"] == "publicado" and viejo["revisado_por"] == "ed"  # separar no cambia la revisión
    assert nuevo["notas"] == ["n2"] and nuevo["estado"] == "pendiente" and nuevo["tipo"] == "hurto_motos"
    assert nuevo["fecha"] == "2026-11-11" and nuevo["barrio"] == "La Luz" and nuevo["no_unir_con"] == ["n1"]


def test_no_separa_el_ultimo_enlace():
    r = correr(f"return RV.aplicar([{json.dumps(CASO)}], {{x:{{separar:['n1','n2']}}}}, 'yo', '2026-11-24', {json.dumps(NOTAS)})")
    assert len(r["casos"]) == 1 and r["casos"][0]["notas"] == ["n1", "n2"]


def test_descartar_como_captura_guarda_el_motivo():
    r = correr(f"return RV.aplicar([{json.dumps(CASO)}], {{x:{{estado:'descartado',motivo_descarte:'captura_o_judicial'}}}}, 'yo', '2026-11-24')")
    c = r["casos"][0]
    assert c["estado"] == "descartado" and c["motivo_descarte"] == "captura_o_judicial" and c["revisado_por"] == "yo"


@pytest.mark.parametrize("titular", [
    "Golpe al crimen en Barranquilla: capturan a 'El Mello', señalado de múltiples homicidios",
    "Capturan a sicario tras asesinar a un hombre en Rebolo",
    "¡Cayó alias 'Breyner' con un revólver!",
    "Hombre cayó muerto tras recibir varios disparos",
    "Envían a la cárcel a presunto asesino de comerciante",
])
def test_captura_igual_que_el_scraper(titular):
    assert correr(f"return RV.esCaptura({json.dumps(titular)})") == es_captura_o_judicial(titular)
