from datetime import datetime

from scraper.fuentes import FUENTES
from scraper.lectores import BOGOTA
from scraper.salud import aviso, medios_callados


def test_medios_callados():
    ahora = datetime(2026, 11, 24, 7, tzinfo=BOGOTA)
    notas = [{"medio": f.nombre, "fecha_captura": "2026-11-23T06:46:46-05:00"} for f in FUENTES[1:]]
    notas.append({"medio": FUENTES[1].nombre, "fecha_captura": "2026-11-01T06:00:00-05:00"})
    notas.append({"medio": FUENTES[0].nombre, "fecha_captura": "2026-11-12T11:09:48-05:00"})
    callados = medios_callados(notas, ahora, dias=3)
    assert callados == [(FUENTES[0].nombre, "2026-11-12T11:09:48-05:00")]
    assert "2026-11-12" in aviso(callados, 3)
    assert medios_callados([], ahora)[0][1] is None  # un medio sin ninguna nota también avisa
