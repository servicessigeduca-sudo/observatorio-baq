# Observatorio BAQ

Mapa y tablero abiertos de los delitos reportados por la prensa en Barranquilla y su área metropolitana. Es un proyecto periodístico.

Los datos salen de notas publicadas por medios locales. De cada nota se guarda solo el titular, la fecha, el enlace y un resumen corto. Cada punto del mapa enlaza a la nota original.

## Scraper

```bash
pip install -r requirements.txt
python -m scraper                          # todas las fuentes
python -m scraper --fuentes zona-cero -v   # una fuente, con detalle
```

Escribe `data/notas.json`: una entrada por nota con `id`, `medio`, `url`, `titular`, `resumen` (máx. 300 caracteres), `fecha_publicacion`, `fecha_captura`, `tipos_delito`, `municipio`, `barrio` y `estado` (`pendiente` al llegar). Las notas ya guardadas no se vuelven a abrir ni se sobrescriben, así que las correcciones del equipo se conservan.

### Fuentes

| Prioridad | Medio | Método |
| --- | --- | --- |
| 1 | Zona Cero | Sección `/judiciales` y metadatos de cada nota |
| 1 | Diario La Libertad | Sección Crónica Judicial, 10 s entre peticiones (su `Crawl-delay`) |
| 2 | Emisora Atlántico | RSS, categoría Judiciales |
| 3 | Impacto News | RSS, categoría Judiciales |
| 3 | CTV Barranquilla | Sección `/category/judiciales` y metadatos de cada nota |

Quedan fuera El Heraldo y El Tiempo, porque prohíben el scraping sin permiso escrito, y ADN Barranquilla, La Cháchara y Q'hubo Barranquilla, porque bloquean el acceso.

### Reglas

- User-agent propio (`ObservatorioBAQ/0.1`) con enlace a este repositorio.
- Lee el `robots.txt` de cada medio y no visita rutas prohibidas. Si el `robots.txt` no se puede leer o responde 401/403, no visita ese medio.
- Al menos 5 s entre peticiones al mismo dominio, o el `Crawl-delay` del medio si es mayor.
- No guarda el cuerpo de los artículos, las fotos ni los comentarios. Tampoco se usa el contenido para entrenar modelos de IA (La Libertad y CTV lo prohíben con `ai-train=no`).
- La clasificación de tipo de delito, municipio y barrio se hace por palabras clave y es provisional: el equipo la revisa antes de publicar un caso.

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest
```
