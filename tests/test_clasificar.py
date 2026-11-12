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
