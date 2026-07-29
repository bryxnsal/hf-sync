# HF Sync

Sincroniza repositorios de Hugging Face a cualquier almacenamiento en la nube (Google Drive, Dropbox, S3, etc.) usando aria2 + rclone.

```
CLI → Scheduler → Coordinator → Downloader → Uploader → Verifier → Cleanup
```

Descarga archivos de un repo de HF con aria2, los sube a la nube con rclone, verifica integridad y limpia archivos temporales.

## Requisitos

- **Python ≥ 3.12**
- **aria2** — descarga multihilo con soporte RPC
- **rclone** — subida a cualquier proveedor cloud
- **uv** (recomendado) — gestor de proyectos Python

Instalación de dependencias del sistema:

```bash
# Debian / Ubuntu
sudo apt install aria2 rclone

# Arch
sudo pacman -S aria2 rclone

# macOS
brew install aria2 rclone
```

## Instalación

### One-liner (recomendado)

```bash
curl -fsSL https://raw.githubusercontent.com/bryxnsal/hf-sync/main/install.sh | bash
```

Detecta `uv` o `pip3` automáticamente e instala `hf-sync` como comando global.

### Manual

```bash
git clone https://github.com/bryxnsal/hf-sync.git
cd hf-sync
uv sync
uv tool install .
hf-sync doctor
```

## Desinstalación

### One-liner

```bash
curl -fsSL https://raw.githubusercontent.com/bryxnsal/hf-sync/main/uninstall.sh | bash
```

Elimina el binario, limpia archivos temporales, y pregunta si deseas eliminar la base de datos local.

### Manual

```bash
uv tool uninstall hf-sync
rm -rf /tmp/hf-sync*
# Opcional: eliminar base de datos y configuración
rm -rf ~/.local/share/hf-sync
```

## Uso rápido

Sin configurar nada, solo necesitas el token de HF:

```bash
# Guarda el token (solo una vez)
hf-sync auth hf_xxxxxxxxxxxx

# Descarga un repo y súbelo a Google Drive
hf-sync start "databricks/dolly-v2-3b" "googledrive:models/dolly"

# O a una carpeta local
hf-sync start "databricks/dolly-v2-3b" "/mnt/disco/models"
```

Eso es todo. aria2 y rclone usan sus configuraciones por defecto.

## Uso detallado

### `hf-sync auth <token>`

Guarda el token de Hugging Face en la base de datos local (validado contra la API de HF).

```bash
hf-sync auth hf_xxxxxxxxxxxx
```

### `hf-sync config`

Configura settings de forma interactiva (Enter para mantener valor por defecto). Los valores se guardan en la base de datos local.

```bash
hf-sync config
```

Las variables disponibles son:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `HF_REPO_ID` | — | ID del repo. Obligatorio si no se pasa en CLI |
| `ARIA2_RPC_URL` | `http://localhost:6800/jsonrpc` | URL del RPC de aria2 |
| `ARIA2_RPC_SECRET` | — | Secreto RPC de aria2 |
| `RCLONE_REMOTE` | — | Remote de rclone. Obligatorio si no se pasa en CLI |
| `RCLONE_PATH` | — | Ruta dentro del remote |

La prioridad de configuración es:

1. **Argumentos CLI** — por invocación
2. **Variables de entorno** — `export HF_REPO_ID=...`
3. **Base de datos** — persistente vía `hf-sync config`
4. **Valores por defecto** — hardcodeados

### `hf-sync doctor`

Verifica dependencias del sistema: aria2, rclone, token HF, acceso a Drive, espacio libre, permisos.

```bash
hf-sync doctor
```

### `hf-sync init [repo_id]`

Escanea un repo de HF e indexa los archivos pendientes en la base de datos.

```bash
# con repo_id desde .env
hf-sync init

# pasando el repo directamente
hf-sync init databricks/dolly-v2-3b
```

### `hf-sync start [repo_id] [destino]`

Inicia el pipeline de sincronización. Por cada archivo:

1. **Downloader** — descarga con aria2
2. **Uploader** — sube con rclone
3. **Verifier** — verifica tamaño y hash
4. **Cleanup** — elimina el temporal

```bash
# todo en CLI (no necesita .env)
hf-sync start databricks/dolly-v2-3b googledrive:models/dolly

# solo repo_id (destino desde .env)
hf-sync start databricks/dolly-v2-3b

# solo destino (repo_id desde .env)
hf-sync start -- googledrive:models/dolly

# todo desde .env
hf-sync start
```

#### `--dry-run`

Pre-flight: verifica acceso al repo, encuentra el archivo más grande, comprueba espacio en disco local y en el destino. No descarga ni sube nada.

```bash
hf-sync start --dry-run "databricks/dolly-v2-3b" "googledrive:models/dolly"

# Ejemplo de salida:
#   Repo: databricks/dolly-v2-3b       ✓
#     Archivos                         42
#     Total                            8.2G
#     Más grande                       pytorch_model.bin (3.4G)
#   Disco local (38.75G libre)         ✓
#   Destino: googledrive:models/dolly ✓
#     Espacio remoto (95G libre)       ✓
```

Si el repo no existe, el token no tiene acceso o no hay suficiente espacio, te lo advierte antes de empezar.

### `hf-sync resume`

Reintenta archivos que fallaron (los marca como `PENDING`).

```bash
hf-sync resume
hf-sync start  # reanuda
```

### `hf-sync verify`

Verifica integridad de archivos ya sincronizados.

```bash
hf-sync verify
```

## Configuración

Tres formas de configurar, de mayor a menor prioridad:

1. **Argumentos CLI** — por invocación
2. **Variables de entorno** — `export HF_TOKEN=...`
3. **Base de datos** — persistente vía `hf-sync auth` y `hf-sync config`
4. **Valores por defecto** — hardcodeados

### Sin configuración persistente

Para uso puntual, solo necesitas el token:

```bash
export HF_TOKEN=hf_xxxxxxxxxxxx
hf-sync start "databricks/dolly-v2-3b" "googledrive:models/dolly"
```

El resto tiene valores por defecto que funcionan si aria2 y rclone están configurados.

### Con configuración persistente (DB)

```bash
# Token (validado contra HF API)
hf-sync auth hf_xxxxxxxxxxxx

# Settings interactivos (Enter para mantener valor)
hf-sync config
```

Luego puedes solo escribir:

```bash
hf-sync start
```

### Variables de entorno

Cualquier setting puede sobrescribirse vía variable de entorno (tiene prioridad sobre DB):

| Variable | Descripción |
|----------|-------------|
| `HF_TOKEN` | Token de Hugging Face (read) |
| `HF_REPO_ID` | ID del repo |
| `ARIA2_RPC_URL` | URL del RPC de aria2 |
| `ARIA2_RPC_SECRET` | Secreto RPC de aria2 |
| `RCLONE_REMOTE` | Remote de rclone |
| `RCLONE_PATH` | Ruta dentro del remote |
| `LOG_LEVEL` | Nivel de log (`INFO`, `DEBUG`, etc.) |

### Servicios externos

aria2 con RPC:

```bash
aria2c --enable-rpc --rpc-listen-all
```

Configurar remote de rclone:

```bash
rclone config
```

### Scripts auxiliares

```bash
scripts/start-aria2.sh   # inicia aria2 como daemon
scripts/stop-aria2.sh    # detiene aria2
scripts/doctor.sh        # verifica dependencias del sistema
```

## Arquitectura

```
src/hf_sync/
├── cli.py              # CLI con Typer
├── config.py           # Config con pydantic-settings
├── logger.py           # Logging con loguru
├── database.py         # Modelos SQLite (SQLModel)
├── models.py           # Modelos de dominio
├── scheduler.py        # Planificador
├── engine/
│   ├── coordinator.py  # Orquesta el pipeline
│   ├── downloader.py   # Descarga con aria2
│   ├── uploader.py     # Sube con rclone
│   ├── verifier.py     # Verifica integridad
│   └── cleanup.py      # Limpia archivos temporales
├── services/
│   ├── huggingface.py  # Hugging Face Hub API
│   ├── aria2.py        # Cliente JSON-RPC
│   ├── rclone.py       # Wrapper subprocess
│   └── doctor.py       # Diagnóstico del sistema
├── repositories/
│   └── files.py        # SQLite queries
├── ui/
│   ├── dashboard.py    # Dashboard en vivo
│   ├── progress.py     # Seguimiento de progreso
│   └── tables.py       # Tablas con Rich
├── types/
│   ├── enums.py        # Status enum
│   └── dto.py          # Data transfer objects
└── utils/
    ├── bytes.py        # Formateo de bytes
    ├── eta.py          # Cálculo de ETA
    ├── hashing.py      # SHA-256
    ├── subprocess.py   # Ejecutar comandos
    └── paths.py        # Rutas del proyecto
```

## Base de datos

Dos tablas en SQLite (`~/.local/share/hf-sync/state.db`):

- **files** — archivos sincronizados (id, filename, size, sha256, status, remote_path, local_path, created_at, updated_at)
- **events** — historial de eventos (id, file_id, event, message, timestamp)

## Desarrollo

```bash
uv sync --group dev
uv run basedpyright src/   # typecheck
uv run pytest              # tests
```

## Licencia

MIT
