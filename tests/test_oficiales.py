import io

import pandas as pd

from oficiales.__main__ import anios_de
from oficiales.procesar import a_json, agregar, categoria, leer


def excel(cab, filas, relleno=3):
    buf = io.BytesIO()
    pd.concat([pd.DataFrame([[None] * len(cab)] * relleno), pd.DataFrame([cab] + filas)]).to_excel(buf, header=False, index=False)
    buf.seek(0)
    return buf


CAB26 = ["ARMAS MEDIOS", "DEPARTAMENTO", "MUNICIPIO", "FECHA ISSO", "GENERO", "CODIGO DANE", "DELITO", "MES", "CANTIDAD", "EDAD ETARIA", "ICCS"]


def test_categoria_por_codigo_y_por_nombre():
    assert categoria("(0101) Homicidio intencional") == "homicidio"
    assert categoria("(050212) Hurto a motocicletas") == "hurto_motos"
    assert categoria("(99) Algo nuevo") == "otros"
    assert categoria("HURTO MOTOCICLETAS") == "hurto_motos"
    assert categoria("HOMICIDIO") == "homicidio"


def test_filtra_area_y_agrega():
    buf = excel(CAB26, [
        ["ARMA DE FUEGO", "ATLÁNTICO", "Barranquilla", "2026/01/02", "MASCULINO", "08001", "(0101) Homicidio intencional", "01", "1", "DE 18 AÑOS Y MÁS", ""],
        ["ARMA DE FUEGO", "ATLÁNTICO", "Barranquilla", "2026/01/05", "MASCULINO", "8001", "(0101) Homicidio intencional", "01", "2", "DE 18 AÑOS Y MÁS", ""],
        ["SIN EMPLEO DE ARMAS", "ATLÁNTICO", "Soledad", "2026/02/01", "FEMENINO", "08758", "(05022) Hurto a personas", "02", "1", "", ""],
        ["ARMA DE FUEGO", "HUILA", "Neiva", "2026/01/01", "FEMENINO", "41001", "(0101) Homicidio intencional", "01", "1", "", ""],
    ])
    t = agregar(leer(buf))
    assert t["mensual"][(2026, 1, "Barranquilla", "homicidio")] == 3
    assert t["mensual"][(2026, 2, "Soledad", "hurto_personas")] == 1
    assert sum(t["mensual"].values()) == 4
    assert t["armas"][(2026, "Barranquilla", "homicidio", "ARMA DE FUEGO")] == 3
    assert t["dias"][(2026, 1, "Barranquilla", "homicidio", 4)] == 1  # 2 de enero de 2026 es viernes
    assert t["genero"][(2026, "Soledad", "hurto_personas", "FEMENINO")] == 1
    assert t["edad"][(2026, "Soledad", "hurto_personas", "NO REPORTADO")] == 1
    j = a_json(t, [], "2026-11-12")
    assert j["ultimo_mes"] == {"anio": 2026, "mes": 2}
    assert j["tablas"]["mensual"]["filas"][0] == [2026, 1, "Barranquilla", "homicidio", 3]


def test_columnas_de_2025():
    cab = ["ARMAS MEDIOS", "DEPARTAMENTO", "MUNICIPIO", "FECHA HECHO", "GENERO", "*AGRUPA EDAD PERSONA*", "CODIGO DANE", "DELITOS", "MES", "CANTIDAD", "ICCS"]
    buf = excel(cab, [["ARMA DE FUEGO", "ATLÁNTICO", "Barranquilla", "2025/03/02", "MASCULINO", "ADULTOS", "08001", "(0101) Homicidio intencional", "03", "1", "0101"]], relleno=0)
    t = agregar(leer(buf))
    assert t["mensual"][(2025, 3, "Barranquilla", "homicidio")] == 1
    assert t["edad"][(2025, "Barranquilla", "homicidio", "ADULTOS")] == 1


def test_anios_de():
    assert anios_de("2020-2022") == [2020, 2021, 2022]
    assert anios_de("2025,2026") == [2025, 2026]
