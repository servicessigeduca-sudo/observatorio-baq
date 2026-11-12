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


# --- Histórico anterior a 2020 -------------------------------------------------

import pandas as pd
from collections import Counter

from oficiales.historico import clasificar, elegir
from oficiales.procesar import _dane, _fechas, agregar as _agregar


def test_clasificar_archivos_viejos():
    assert clasificar("Homicidio Intencional 2019.xlsx") == ("homicidio", "homicidio", 2019)
    assert clasificar("homicidios_en_accidente_de_transito_2019.xlsx") == ("homicidio_transito", "transito", 2019)
    assert clasificar("lesiones_en_accidente_de_transito_2018_0.xlsx") == ("lesiones_transito", "transito", 2018)
    assert clasificar("lesiones_personales_2018_1.xlsx")[1] == "lesiones"
    assert clasificar("hurto_motocicletas_2018_2.xlsx")[1] == "hurto_motos"
    assert clasificar("hurto_automotores_2018_2.xlsx")[1] == "hurto_carros"
    assert clasificar("hurto_a_personas_2010_0.xlsx")[1] == "hurto_personas"
    assert clasificar("abigeato_2019_3.xlsx") is None
    assert clasificar("hurto a personas.xlsx") is None  # sin año


def test_codigo_dane_y_fechas_en_varios_formatos():
    assert list(_dane(pd.Series(["08001", "8001", "08001000", "8001000.0", "8758000"]))) == ["08001", "08001", "08001", "08001", "08758"]
    f = _fechas(pd.Series(["2015-03-04 00:00:00", "04/03/2015", "20150304"]))
    assert list(f.dt.month) == [3, 3, 3] and list(f.dt.day) == [4, 4, 4]


def test_agregar_archivo_de_un_solo_delito():
    df = pd.DataFrame({
        "FECHA": ["2012-01-05", "2012-01-06", "2012-02-01"],
        "DEPARTAMENTO": ["ATLÁNTICO"] * 3,
        "MUNICIPIO": ["Barranquilla (CT)", "Soledad", "Barranquilla (CT)"],
        "CODIGO DANE": ["8001000", "8758000", "11001000"],
        "CANTIDAD": ["1", "2", "1"],
    })
    t = _agregar(df, cat="homicidio")
    assert t["mensual"] == Counter({(2012, 1, "Barranquilla", "homicidio"): 1, (2012, 1, "Soledad", "homicidio"): 2})


def test_agregar_sin_codigo_dane_usa_el_nombre():
    df = pd.DataFrame({"FECHA": ["2011-07-01"], "DEPARTAMENTO": ["ATLÁNTICO"], "MUNICIPIO": ["Malambo"], "CANTIDAD": ["3"]})
    assert _agregar(df, cat="lesiones")["mensual"] == Counter({(2011, 7, "Malambo", "lesiones"): 3})


def test_elegir_versiones_no_cuenta_dos_veces():
    def t(meses, n):
        return {"mensual": Counter({(2018, m, "Barranquilla", "hurto_carros"): n for m in meses})}
    completa, parcial, otra_mitad = t(range(1, 13), 10), t(range(1, 7), 9), t(range(7, 13), 9)
    assert [u for u, _ in elegir([("a", parcial), ("b", completa)])] == ["b"]
    assert sorted(u for u, _ in elegir([("a", t(range(1, 7), 5)), ("b", otra_mitad)])) == ["a", "b"]


def test_cobertura_pide_todos_los_archivos_de_la_categoria():
    from oficiales.historico import cobertura
    r = Counter({(2015, "homicidio"): 5, (2015, "homicidio_transito"): 2, (2016, "homicidio_transito"): 1, (2016, "lesiones_transito"): 3})
    c = cobertura(r, [2015, 2016])
    assert [2015, "homicidio"] in c and [2016, "transito"] in c
    assert [2015, "transito"] not in c and [2016, "homicidio"] not in c


def test_conservar_no_borra_lo_que_ya_estaba():
    from oficiales.historico import conservar
    previo = {"cobertura": [[2011, "homicidio"], [2014, "lesiones"]], "archivos": ["a.xlsx"], "tablas": {
        "mensual": {"filas": [[2011, 1, "Barranquilla", "homicidio", 40], [2014, 1, "Barranquilla", "lesiones", 9]]},
        "armas": {"filas": [[2011, "Barranquilla", "homicidio", "ARMA DE FUEGO", 30]]}}}
    tablas = {"mensual": Counter({(2014, 1, "Barranquilla", "lesiones"): 10}), "armas": Counter()}
    cob, extra = conservar(tablas, [[2014, "lesiones"]], previo)
    assert [2011, "homicidio"] in cob and extra == ["a.xlsx"]
    assert tablas["mensual"][(2011, 1, "Barranquilla", "homicidio")] == 40
    assert tablas["mensual"][(2014, 1, "Barranquilla", "lesiones")] == 10  # no se duplica
    assert tablas["armas"][(2011, "Barranquilla", "homicidio", "ARMA DE FUEGO")] == 30


def test_siedco_manual_llena_solo_lo_que_falta(tmp_path):
    from oficiales.manual import completar
    df = pd.DataFrame({
        "Temática": ["HOMICIDIOS"] * 3, "Año": ["2005", "2005", "2010"], "Mes": ["Enero", "Febrero", "Enero"],
        "Departamento": ["ATLÁNTICO"] * 3, "Código Dane": ["08001000", "08758000", "08001000"],
        "Municipio": ["BARRANQUILLA (CT)", "SOLEDAD", "BARRANQUILLA (CT)"], "Armas / Medios": ["ARMA DE FUEGO"] * 3,
        "Agrupa Edad Persona": ["ADULTOS"] * 3, "Género": ["MASCULINO"] * 3, "Día": ["dom.", "mié.", "lun."], "Cantidad": ["2", "1", "5"],
    })
    df.to_excel(tmp_path / "h.xlsx", index=False)
    tablas = {k: Counter() for k in ["mensual", "armas", "dias", "genero", "edad"]}
    cob = {(2010, "homicidio")}
    completar(tablas, cob, tmp_path)
    assert tablas["mensual"] == Counter({(2005, 1, "Barranquilla", "homicidio"): 2, (2005, 2, "Soledad", "homicidio"): 1})
    assert tablas["dias"][(2005, 1, "Barranquilla", "homicidio", 6)] == 2
    assert (2005, "homicidio") in cob


def test_nombres_de_siedco():
    from oficiales.procesar import categoria
    assert categoria("HURTO A AUTOMOTORES") == "hurto_carros"
    assert categoria("HURTO A MOTOCICLETAS") == "hurto_motos"
    assert categoria("DELITOS SEXUALES") == "violencia_sexual"
    assert categoria("HURTO A ENTIDADES FINANCIERAS") == "hurto_entidades"
