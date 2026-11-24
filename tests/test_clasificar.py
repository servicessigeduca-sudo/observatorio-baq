import pytest

from scraper.clasificar import barrio, clasificar, municipio, tipos_delito


@pytest.mark.parametrize(
    "titular, esperado",
    [
        ("Un hombre fue asesinado a bala en el barrio Las Flores", "homicidio"),
        ("Sicarios en moto asesinan a vigilante informal en el barrio El Santuario de Barranquilla", "homicidio"),
        ("Falleció la mujer de 43 años blanco de atentado a bala en el barrio El Valle", "homicidio"),
        ("Mujer de 42 años fue baleada dentro de un establecimiento comercial en el barrio El Valle", "lesiones"),
        ("Capturan en Barranquilla a alias 'Danielito', señalado de extorsiones", "extorsion"),
        ("Investigan feminicidio en Soledad", "feminicidio"),
        ("Atracan a comerciante y le roban $5 millones en Rebolo", None),
    ],
)
def test_tipo_principal(titular, esperado):
    tipos = tipos_delito(titular)
    if esperado is None:
        assert "homicidio" not in tipos
    else:
        assert esperado in tipos


def test_homicidio_sin_palabra_muerte():
    assert tipos_delito("Mataron a bala a hombre cuando caminaba por La Esmeralda")[0] == "homicidio"


def test_feminicidio_tambien_cuenta_como_homicidio():
    assert tipos_delito("Investigan feminicidio en Soledad")[:2] == ["feminicidio", "homicidio"]


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Asesinan a tiros a vigilante informal en el barrio Ciudad Paraíso de Soledad", "Soledad"),
        ("Mototaxista fue asesinado por sicarios en el barrio Mundo Feliz, en Galapa", "Galapa"),
        ("Joven asesinado en El Bosque, suroccidente de Barranquilla", "Barranquilla"),
        ("Incautan licor adulterado en Sabanalarga", "fuera_del_area"),
        ("Hombre asesinado en Villate", None),
    ],
)
def test_municipio(texto, esperado):
    assert municipio(texto) == esperado


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Sicarios asesinan a vigilante informal en el barrio El Santuario de Barranquilla", "El Santuario"),
        ("Asesinan a tiros a vigilante en el barrio Ciudad Paraíso de Soledad", "Ciudad Paraíso"),
        ("Mototaxista asesinado en el barrio Mundo Feliz, en Galapa", "Mundo Feliz"),
        ("Asesinan a madre e hija en Terranova II", "Terranova"),
        ("Asesinan a un hombre en Villate: una bala perdida impactó a una mujer", "Villate"),
        ("Capturan a alias 'El Chino' en Soledad", None),
    ],
)
def test_barrio(texto, esperado):
    assert barrio(texto) == esperado


def test_clasificar_combina_titular_y_resumen():
    c = clasificar("Ataque sicarial deja un muerto", "El hecho ocurrió en el barrio Rebolo de Barranquilla.")
    assert c == {"tipos_delito": ["homicidio"], "municipio": "Barranquilla", "barrio": "Rebolo"}


@pytest.mark.parametrize(
    "titular, es_captura",
    [
        ("Golpe al crimen en Barranquilla: capturan a 'El Mello', señalado de múltiples homicidios", True),
        ("Policía reporta dos capturados por ataques a Supertiendas Olímpica en Barranquilla", True),
        ("Condenan a 40 años a hombre que asesinó a su pareja", True),
        ("Imputan homicidio a joven que mató a su vecino", True),
        ("Envían a la cárcel a presunto asesino de comerciante", True),
        ("¡Cayó alias 'Breyner' con un revólver!", True),
        ("Capturan a sicario tras asesinar a un hombre en Rebolo", False),
        ("Sicarios asesinan a alias 'Kevin Toyota', señalado jefe de 'Los del Freseo'", False),
        ("Asesinan a hombre que había salido de la cárcel", False),
        ("Hombre cayó muerto tras recibir varios disparos", False),
    ],
)
def test_captura_o_judicial(titular, es_captura):
    tipos = clasificar(titular)["tipos_delito"]
    assert (tipos[:1] == ["captura"]) == es_captura


@pytest.mark.parametrize(
    "titular, tipo",
    [
        ("Le roban la moto a domiciliario en Rebolo", "hurto_motos"),
        ("Atracan supertienda Olímpica en el norte de Barranquilla", "hurto_comercio"),
        ("Roban celular a mujer en el centro", "hurto_personas"),
        ("Le robaron 20 millones al salir del banco", "hurto_entidades"),
        ("Ladrones entraron a una casa en El Prado y robaron joyas", "hurto_residencias"),
        ("Se robaron una camioneta en el norte", "hurto_carros"),
        ("Amenazan a comerciantes con panfletos en Soledad", "amenazas"),
    ],
)
def test_categorias_de_la_base_oficial(titular, tipo):
    assert clasificar(titular)["tipos_delito"][0] == tipo
