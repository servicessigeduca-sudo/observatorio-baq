# Estructura del sitio y wireframes

Un solo sitio para toda la ciudadanía: el mismo contenido y el mismo análisis para vecinos, periodistas, investigadores y autoridades. Cada tema se puede leer en tres niveles: **resumen** (portada y titulares), **informe completo** (Informes) y **datos descargables con metodología** (Metodología y datos).

## Mapa del sitio

| Navegación | Archivo | Qué responde | Datos |
| --- | --- | --- | --- |
| Inicio | `index.html` | ¿Qué pasó esta semana y en mi barrio? | `publico/resumen.json`, `publico/prensa.json`, `publico/registro.json` |
| Mapa | `mapa.html` | ¿Dónde se concentran los casos? | `publico/registro.json`, `publico/prensa.json` |
| Informes | `informes.html` (`?p=AAAA-MM`) | ¿Qué pasó en un mes, con contexto? | `publico/informes/*.json` |
| Estadísticas oficiales | `estadisticas.html` | ¿Qué registra la Policía desde 2003? | `oficiales.json` |
| Prensa vs. oficial | `prensa-oficial.html` | ¿Qué parte llega a los medios y dónde hay vacíos? | `publico/prensa_vs_oficial.json` |
| Metodología y datos | `metodologia.html` | ¿De dónde sale cada cifra y cómo la descargo? | `publico/diccionario.json` |

Elementos comunes a todas las páginas: cabecera con la navegación de seis entradas, cambio de modo claro y oscuro, franja con fuente y fecha de corte, pie con licencia y cita sugerida. Un archivo HTML por página; estilos en `estilos.css`, utilidades en `comun.js` y `datos.js`. Librerías solo por CDN con versión fija (Leaflet 1.9.4).

## Fuentes que combina el sitio

| Fuente | Cubre | Nivel más fino publicado | Se actualiza |
| --- | --- | --- | --- |
| Prensa local (5 medios) | Todos los delitos que llegan a la prensa | Barrio y mes; enlace a la nota | Cada día, 6:00 a. m. |
| Registro de homicidios (capa ArcGIS) | Homicidios en los 5 municipios desde enero de 2026 | Zona de cuadrícula fusionada, barrio y mes | Cuando se carga una nueva copia |
| Policía Nacional (SIEDCO) | 15 delitos desde 2003 | Municipio y mes | Día 5 de cada mes |

## Wireframes

### Inicio (celular, 360 px)

```
┌──────────────────────────────┐
│ ▣ Observatorio BAQ      ( ☾ )│
│ Inicio Mapa Informes Estad…  │ ← navegación desplazable
├──────────────────────────────┤
│ ESTA SEMANA · 6–12 nov       │
│ 34 casos reportados en la    │ ← titular de datos
│ prensa                       │
│ ▲ +12 % frente a la anterior │ (o "sin comparación: la
│ Más casos: Barranquilla (10) │  semana anterior está incompleta")
│ Actualizado 13 nov, 6:10 a.m.│
├──────────────────────────────┤
│ 🔍 Busca tu barrio o municipio│
│ [ Rebolo                   ] │
│ ┌──────────────────────────┐ │
│ │ Rebolo · Barranquilla    │ │
│ │ 12 homicidios en 2026    │ │
│ │ ▁▂▃▂▅▃ tendencia mensual │ │
│ │ 2,1× el promedio de los  │ │
│ │ barrios de Barranquilla  │ │
│ │ Casos recientes (tarjetas)│ │
│ └──────────────────────────┘ │
├──────────────────────────────┤
│ [ mapa estático, toca para   │ ← no atrapa el scroll;
│   explorar ]                 │   botón "Abrir el mapa"
├──────────────────────────────┤
│ Fuentes y límites (3 líneas) │
│ → Metodología                │
├──────────────────────────────┤
│ [ Leer el informe de octubre ]│
└──────────────────────────────┘
```

### Inicio (escritorio, 1180 px)

```
┌────────────────────────────────────────────────────────────────────┐
│ ▣ Observatorio BAQ   Inicio  Mapa  Informes  Estadísticas oficiales │
│                      Prensa vs. oficial  Metodología y datos   ( ☾ )│
├───────────────────────────────────────────┬────────────────────────┤
│ ESTA SEMANA · 6 al 12 de noviembre        │  ┌──────────────────┐  │
│ 34 casos reportados en la prensa          │  │ cifra grande     │  │
│ ▲ variación · zona con más casos          │  │ por tipo (barras)│  │
│ Actualizado: 13 nov 2026, 6:10 a. m.      │  └──────────────────┘  │
├───────────────────────────────────────────┴────────────────────────┤
│ Busca tu barrio o municipio  [___________________]                 │
│ ┌ ficha: casos recientes │ tendencia │ vs. promedio │ tasa ───────┐ │
├────────────────────────────────────────────────────────────────────┤
│ Mapa (vista previa)                         │ Leyenda y enlace    │
├────────────────────────────────────────────────────────────────────┤
│ Fuentes y límites                   │ Último informe →            │
└────────────────────────────────────────────────────────────────────┘
```

### Mapa

```
Celular                              Escritorio
┌──────────────────────────────┐     ┌──────────────┬───────────────────────────┐
│ Filtros (hoja desplegable)   │     │ Filtros      │                           │
│ Fuente · Periodo · Delito ·  │     │ Fuente       │         MAPA              │
│ Municipio · Modalidad        │     │ Periodo      │  Vista: Cuadrícula|Barrio|│
├──────────────────────────────┤     │ Delito       │         Calor             │
│ Vista: Cuadrícula|Barrio|Calor│    │ Municipio    │                           │
│ ┌──────────────────────────┐ │     │ Modalidad    │  Leyenda numérica fija    │
│ │ MAPA (gestos con 2 dedos)│ │     │ [Copiar enl.]│                           │
│ └──────────────────────────┘ │     ├──────────────┴───────────────────────────┤
│ Leyenda numérica fija        │     │ Gráfico por mes (título = conclusión)    │
│ Gráfico por mes              │     │ Tabla de zonas / barrios                 │
│ Tabla (tarjetas)             │     └──────────────────────────────────────────┘
└──────────────────────────────┘
```

Los filtros quedan en la URL (`mapa.html?f=registro&v=celdas&d=2026-01&h=2026-10&m=Soledad&mod=Sicariato`), así que un enlace copiado abre la misma vista.

### Informe

```
┌──────────────────────────────┐
│ Informe de octubre de 2026   │
│ [INCOMPLETO] motivo          │
│ Archivo: ‹ sep  · nov ›      │
├──────────────────────────────┤
│ 1. Resumen (3–4 frases)      │
│ 2. Cifras clave (tarjetas)   │
│ 3. Zonas (municipios, barrios│
│    con ≥3 casos)             │
│ 4. Tendencia (12 meses, el   │
│    último marcado incompleto)│
│ 5. Comparación con la Policía│
│ 6. Limitaciones              │
│ Descargar JSON · Cita        │
└──────────────────────────────┘
```

### Prensa vs. oficial

```
┌──────────────────────────────┐
│ Título = conclusión          │
│ Filtros: delito · municipio  │
│ Barras por mes: prensa,      │
│ registro y Policía           │
│ Tabla municipio × mes con    │
│ proporción que llega a medios│
│ (vacío = no comparable)      │
└──────────────────────────────┘
```

## Reglas de diseño

- Mobile first: una columna hasta 620 px; tarjetas en lugar de tablas en celular.
- El mapa no captura el scroll en celular: se mueve con dos dedos y la rueda solo hace zoom con Ctrl/⌘.
- Cada gráfico tiene un título que dice la conclusión y un resumen en texto debajo (también sirve de texto alternativo).
- El último periodo con carga incompleta se dibuja con trama y la etiqueta «incompleto».
- Estados de carga («Cargando…»), error («No se pudieron cargar los datos») y vacío («Sin casos para estos filtros») distintos: nunca un «0» cuando no hay datos.
- Contraste AA, foco visible, todo operable con teclado, `lang="es"`.
