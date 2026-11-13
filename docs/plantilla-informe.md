# Plantilla del informe

Cada informe tiene siempre las mismas seis secciones, en el mismo orden. `python -m publico` genera un informe por mes en `data/publico/informes/AAAA-MM.json`, y `informes.html?p=AAAA-MM` lo muestra. El archivo de todos los informes está en `informes/index.json`.

## Encabezado
- **Título:** «Informe de ‹mes› de ‹año›».
- **Estado:** `completo` o `incompleto`. Es incompleto si el mes no ha terminado, si la fuente llega solo hasta una fecha dentro del mes, o si el mes tiene menos del 60 % de la mediana de los seis meses anteriores en los dos últimos meses antes del corte (posible retraso en la carga). El motivo se muestra siempre.
- **Fuente principal y fecha de corte.**

## 1. Resumen
Tres o cuatro frases en lenguaje claro, sin adjetivos que dramaticen ni minimicen:
1. Cuántos casos hubo y según qué fuente.
2. Comparación con el mes anterior, solo si ambos meses están completos.
3. Barrio con más casos, solo si tiene 3 o más.
4. Cifra de la Policía del mismo mes, si ya está publicada.

## 2. Cifras clave
Tarjetas: homicidios según el registro (con variación), según la Policía, según la prensa, y la participación de la modalidad más frecuente.

## 3. Zonas
Casos por municipio y barrios con 3 casos o más. Los barrios con menos no se nombran.

## 4. Tendencia
Los últimos 12 meses de cada fuente. El título del gráfico dice la conclusión (por ejemplo, «Junio fue el mes con más homicidios del año»), y debajo hay un resumen en texto. El último mes incompleto se dibuja con trama.

## 5. Comparación con cifras oficiales
Registro, Policía y prensa del mismo mes. Si la Policía aún no publica el mes, se dice así, y no se pone un cero.

## 6. Limitaciones
Lista fija más las que apliquen ese mes:
- La prensa no cubre todos los casos.
- El registro y la Policía pueden diferir por fecha de corte, criterio y municipio asignado.
- Los barrios con menos de 3 casos no se nombran.
- Los datos muestran cuántos casos hubo, dónde y cuándo, pero no permiten atribuir causas.
- Cobertura parcial de prensa antes del inicio de la recolección automática.

## Pie
Descarga del informe en JSON, licencia y cita sugerida:

> Observatorio BAQ (‹año›). Informe de ‹mes› de ‹año›. Datos abiertos sobre delitos en Barranquilla y su área metropolitana. https://servicessigeduca-sudo.github.io/observatorio-baq/informes.html?p=‹AAAA-MM›
