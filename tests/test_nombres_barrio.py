import json
import shutil
import subprocess
from pathlib import Path

import pytest

from casos.__main__ import deducir_municipio
from publico.construir import oficializar_registro
from publico.nombres_barrio import Referencia, clave
from scraper.clasificar import barrio, clasificar


def _f(barrio, municipio, otros=()):
    return {"type": "Feature", "properties": {"barrio": barrio, "municipio": municipio, "clave": clave(barrio), "otros": list(otros)}, "geometry": None}


GEO = {"features": [
    _f("7 de Abril", "Barranquilla"), _f("Limon", "Barranquilla"), _f("Santo Domingo de Guzman", "Barranquilla"),
    _f("Los Almendros", "Soledad"), _f("Villa María", "Soledad"), _f("Villa María", "Puerto Colombia"),
    _f("Mundo Feliz II", "Galapa"),
]}
REF = Referencia(GEO, {"Barranquilla|Santo Domingo": "Santo Domingo de Guzman"})


def test_clave_numeros_y_etapas():
    assert clave("Siete de Abril") == clave("7 de Abril") == "7 de abril"
    assert clave("Los Olivos II") == clave("Los Olivos 2") == "los olivos 2"
    assert clave("Mundo Feliz Etapa 2") == clave("Mundo Feliz II")
    assert clave("Barrio El Bosque") == "el bosque"


def test_oficial_con_alias_y_sin_articulo():
    assert REF.oficial("Santo Domingo", "Barranquilla") == "Santo Domingo de Guzman"
    assert REF.oficial("El Limón", "Barranquilla") == "Limon"
    assert REF.oficial("Siete de Abril", "Barranquilla") == "7 de Abril"
    assert REF.oficial("Los Almendros", "Barranquilla") is None


def test_municipio_unico():
    assert REF.municipio_unico("Los Almendros") == "Soledad"
    assert REF.municipio_unico("Villa Maria") is None  # está en dos municipios: no se adivina
    assert REF.municipio_unico("Barrio Inventado") is None


def test_deducir_municipio():
    casos = [{"barrio": "Los Almendros", "municipio": None}, {"barrio": "Villa María", "municipio": None},
             {"barrio": "Los Almendros", "municipio": "Malambo"}]
    assert deducir_municipio(casos, REF) == 1
    assert casos[0] == {"barrio": "Los Almendros", "municipio": "Soledad", "municipio_deducido": True}
    assert casos[1]["municipio"] is None and casos[2]["municipio"] == "Malambo"


def test_registro_une_grafias_del_mismo_barrio():
    reg = {"columnas": [], "filas": [
        ["2026-08", "Barranquilla", "Metropolitana", "Santo Domingo", "h016", "Hombre", "Sicariato", 2],
        ["2026-08", "Barranquilla", "Metropolitana", "Santo Domingo de Guzman", "h016", "Hombre", "Sicariato", 1],
        ["2026-08", "Barranquilla", "Metropolitana", "Rebolo", "h001", "Hombre", "Sicariato", 4],
    ], "barrios": [{"municipio": "Barranquilla", "barrio": "Santo Domingo", "centro": None},
                   {"municipio": "Barranquilla", "barrio": "Santo Domingo de Guzman", "centro": [10.9, -74.8]}]}
    out = oficializar_registro(reg, REF)
    # Se usa la grafía con más casos y se suman las filas iguales.
    assert ["2026-08", "Barranquilla", "Metropolitana", "Santo Domingo", "h016", "Hombre", "Sicariato", 3] in out["filas"]
    assert len(out["filas"]) == 2
    assert out["barrios"] == [{"municipio": "Barranquilla", "barrio": "Santo Domingo", "centro": [10.9, -74.8]}]


def test_barrio_no_toma_nombres_de_clinicas_ni_estaciones():
    c = clasificar("Hieren en atraco a un hombre en Los Robles", "De urgencia fue llevado a la Clínica Los Almendros.")
    assert c["barrio"] is None and "lesiones" in c["tipos_delito"]
    assert barrio("lo atendieron uniformados de la Estación de Policía El Bosque") is None
    assert barrio("Asesinan a un hombre en Los Almendros") == "Los Almendros"


@pytest.mark.skipif(shutil.which("node") is None, reason="sin node")
def test_clave_igual_en_la_pagina():
    nombres = ["Siete de Abril", "Los Olivos II", "Mundo Feliz Etapa 2", "Barrio El Bosque", "Urbanización Villa Olímpica",
               "La Loma de los Chivos- Vía Juan Mina", "Villa San Pedro 2", "Ñapanga", "Primero de Mayo"]
    datos = Path(__file__).resolve().parents[1] / "web" / "datos.js"
    js = ("global.window=global;global.document={addEventListener(){}};"
          f"require({json.dumps(str(datos))});"
          f"console.log(JSON.stringify({json.dumps(nombres)}.map(window.OBAQ.claveBarrio)))")
    salida = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout
    assert json.loads(salida) == [clave(n) for n in nombres]
