import io

import pandas as pd

from oficiales.procesar import a_json, agregar, categoria, leer


def excel(filas):
    cab = ["ARMAS MEDIOS", "DEPARTAMENTO", "MUNICIPIO", "FECHA ISSO", "GENERO", "CODIGO DANE", "DELITO", "MES", "CANTIDAD", "EDAD ETARIA", "ICCS"]
    relleno = pd.DataFrame([[None] * len(cab)] * 3)
    cuerpo = pd.DataFrame([cab] + filas)
    buf = io.BytesIO()
    pd.concat([relleno, cuerpo]).to_excel(buf, header=False, index=False)
    buf.seek(0)
    return buf


def test_categoria_por_codigo():
    assert categoria("(0101) Homicidio intencional") == "homicidio"
    assert categoria("(050212) Hurto a motocicletas") == "hurto_motos"
    assert categoria("(99) Algo nuevo") == "otros"


def test_filtra_area_y_agrega():
    buf = excel([
        ["ARMA DE FUEGO", "ATLÁNTICO", "Barranquilla", "2026/01/02", "MASCULINO", "08001", "(0101) Homicidio intencional", "01", "1", "", ""],
        ["ARMA DE FUEGO", "ATLÁNTICO", "Barranquilla", "2026/01/05", "MASCULINO", "8001", "(0101) Homicidio intencional", "01", "2", "", ""],
        ["SIN EMPLEO DE ARMAS", "ATLÁNTICO", "Soledad", "2026/02/01", "FEMENINO", "08758", "(05022) Hurto a personas", "02", "1", "", ""],
        ["ARMA DE FUEGO", "HUILA", "Neiva", "2026/01/01", "FEMENINO", "41001", "(0101) Homicidio intencional", "01", "1", "", ""],
    ])
    conteo, armas = agregar(leer(buf))
    assert conteo[(2026, 1, "Barranquilla", "homicidio")] == 3
    assert conteo[(2026, 2, "Soledad", "hurto_personas")] == 1
    assert sum(conteo.values()) == 4
    assert armas[(2026, "homicidio", "ARMA DE FUEGO")] == 3
    j = a_json(conteo, armas, [], "2026-11-12")
    assert j["ultimo_mes"] == {"anio": 2026, "mes": 2}


def test_columnas_de_2025_fecha_hecho_y_delitos():
    cab = ["ARMAS MEDIOS", "DEPARTAMENTO", "MUNICIPIO", "FECHA HECHO", "GENERO", "CODIGO DANE", "DELITOS", "CANTIDAD"]
    buf = io.BytesIO()
    pd.DataFrame([cab, ["ARMA DE FUEGO", "ATLÁNTICO", "Barranquilla", "2025-03-02", "M", "08001", "(0101) Homicidio intencional", "1"]]).to_excel(buf, header=False, index=False)
    buf.seek(0)
    conteo, _ = agregar(leer(buf))
    assert conteo[(2025, 3, "Barranquilla", "homicidio")] == 1
