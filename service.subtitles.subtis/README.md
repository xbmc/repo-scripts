# Subtis Subtitles (Kodi)

Addon de servicio de subtítulos para Kodi que usa la API de [Subtis](https://subtis.io) para buscar y descargar subtítulos en español automáticamente.

## Requisitos

- Kodi 19+ (Matrix) con xbmc.python 3.0.0
- Conexión a internet

## Instalación

1. Descarga el ZIP desde `versions/` (ej. `service.subtitles.subtis-X.Y.Z.zip`)
2. En Kodi: **Add-ons** → **Instalar desde archivo ZIP** → selecciona el ZIP
3. Espera la notificación de instalación exitosa

## Uso

1. Reproduce una película en Kodi
2. Abre el menú de subtítulos (tecla `T` o desde el OSD)
3. Selecciona **Subtis** como proveedor
4. El subtítulo se descarga y aplica automáticamente

**Nota**: Series/TV shows aún no están soportados.

## Cómo Funciona

### Flujo de Búsqueda

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Kodi Player    │────▶│  Subtis Addon   │────▶│  subt.is API    │
│  (película)     │     │  (search)       │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │                       │
                                │  1. Primary search    │
                                │  (size + filename)    │
                                │◀──────────────────────│
                                │                       │
                        ┌───────▼───────┐               │
                        │  Found?       │               │
                        └───────┬───────┘               │
                           No   │   Yes                 │
                    ┌───────────┴──────────┐            │
                    │                      │            │
                    ▼                      ▼            │
            2. Alternative         Download & apply     │
            (filename only)        (sync: true)         │
                    │                                   │
                    │◀──────────────────────────────────│
                    ▼
            Download & apply
            (sync: false)
```

### Acciones del Plugin

| Acción     | Descripción                                      |
|------------|--------------------------------------------------|
| `search`   | Busca subtítulos usando nombre y tamaño del archivo |
| `download` | Descarga el subtítulo desde `subtitle_link`      |

### API Endpoints

| Endpoint | Uso |
|----------|-----|
| `GET /v1/subtitle/file/name/{size}/{filename}` | Primario: coincidencia exacta por tamaño + nombre |
| `GET /v1/subtitle/file/alternative/{filename}` | Alternativo: coincidencia difusa solo por nombre |

El addon intenta primero el endpoint primario. Si no encuentra coincidencia, usa el endpoint alternativo. Los subtítulos alternativos se marcan como "no sincronizados" en Kodi ya que pueden no coincidir perfectamente con el archivo de video.

**Respuesta exitosa (200):**
```json
{
  "subtitle": {
    "subtitle_link": "https://...",
    "subtitle_file_name": "Movie.Name.2024.srt"
  },
  "title": {
    "title_name": "Movie Name",
    "year": "2024"
  }
}
```

### Almacenamiento

Los subtítulos descargados se guardan temporalmente en:
```
{kodi_profile}/addon_data/service.subtitles.subtis/temp/
```

## Estructura del Paquete

```
service.subtitles.subtis/
├── addon.xml          # Manifest del addon
├── service.py         # Lógica principal
├── README.md          # Documentación
└── resources/
    └── icon.png       # Icono del addon
```

## Desarrollo

### Construir el ZIP

```bash
cd packages/kodi
python3 build.py
```

El paquete se genera en `versions/service.subtitles.subtis-<versión>.zip`.

### Logs

Los logs del addon usan el prefijo `### SUBTIS ###` y se pueden ver en:
- **Sistema** → **Registro** (habilitar debug)
- Archivo: `~/.kodi/temp/kodi.log`

Ejemplo de log:
```
### SUBTIS ### Search requested but no media is playing
### SUBTIS ### ERROR: No subtitles found or API error (status: 404)
```

### Configuración Requerida

Antes de publicar, actualiza la versión en `addon.xml`:
```xml
<addon id="service.subtitles.subtis" version="X.Y.Z" ...>
```

## Troubleshooting

| Problema | Solución |
|----------|----------|
| "No hay reproducción activa" | Asegúrate de que hay una película reproduciéndose |
| "Película no encontrada" | El archivo no está en la base de datos de Subtis |
| "Soporte para series proximamente" | Las series aún no están soportadas |
| Subtítulo no aparece | Revisa los logs para ver errores de red o API |

## Limitaciones Actuales

- Solo películas (no series/episodios)
- Solo subtítulos en español
- Subtítulos alternativos pueden no estar perfectamente sincronizados
