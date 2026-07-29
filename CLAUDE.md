# HF Sync — AI Guide

## Project Overview

Tool that syncs Hugging Face repos to cloud storage (Google Drive, etc.) via aria2 + rclone.
Pipeline per file: Download (aria2) → Upload (rclone) → Verify → Cleanup.

Written in Python 3.12+. Package manager: `uv`. Entry: `hf-sync` CLI via Typer.

## Architecture

```
src/hf_sync/
├── cli/               # Typer commands, one file per command
│   ├── __init__.py    # Re-exports app, console, shared utils
│   ├── app.py         # app = typer.Typer(), console = Console()
│   ├── commands/      # Each command in separate file
│   │   ├── auth.py    # hf-sync auth <token>
│   │   ├── config.py  # hf-sync config (interactive)
│   │   ├── doctor.py  # hf-sync doctor
│   │   ├── init.py    # hf-sync init [repo_id]
│   │   ├── start.py   # hf-sync start [repo_id] [dest]
│   │   ├── resume.py  # hf-sync resume
│   │   ├── update.py  # hf-sync update
│   │   └── verify.py  # hf-sync verify
│   └── shared/
│       └── display.py # _FrozenBar, _fmt_elapsed, _parse_destination
├── engine/            # Pipeline stages, no IO
│   ├── coordinator.py # Orchestrates: Downloader→Uploader→Verifier→Cleanup
│   ├── downloader.py  # Talks only to Aria2Service
│   ├── uploader.py    # Talks only to RcloneService
│   ├── verifier.py    # Checks size/hash/existence
│   └── cleanup.py     # Removes temp files
├── services/          # External service wrappers, no business logic
│   ├── aria2.py       # JSON-RPC client
│   ├── rclone.py      # Subprocess wrapper (sync + async)
│   ├── huggingface.py # HuggingFace Hub API
│   └── doctor.py      # System health checks + dry-run
├── repositories/
│   └── files.py       # All raw SQL for file CRUD
├── types/
│   ├── dto.py         # Dataclasses: SyncTask, DoctorReport, DryRunReport
│   └── enums.py       # Status enum (PENDING→DOWNLOADING→UPLOADING→VERIFYING→DONE/FAILED)
├── ui/                # Rich TUI components
│   ├── dashboard.py   # Live dashboard (Rich Live)
│   ├── progress.py    # ProgressTracker
│   └── tables.py      # Table rendering utils
├── utils/             # Pure functions
│   ├── bytes.py       # human_size()
│   ├── eta.py         # ETA calculation
│   ├── hashing.py     # sha256()
│   ├── paths.py       # Path helpers
│   └── subprocess.py  # Async subprocess helper
├── config.py          # pydantic-settings singleton, DB override fallback
├── database.py        # SQLModel tables + Database class + sync_get_config
├── models.py          # Additional SQLModel models
├── logger.py          # Loguru setup
└── scheduler.py       # Sync scheduling logic
```

### Layering Rules

| Layer | Can import | Example |
|---|---|---|
| `services/` | nothing from engine/ | `Aria2Service`, `RcloneService` |
| `engine/` | services/, repositories/, types/ | `Downloader(aria2)`, `Uploader(rclone)` |
| `repositories/` | types/ only | `FileRepository(conn)` |
| `ui/` | Rich only | `Dashboard`, `ProgressTracker` |
| `cli/commands/` | anything | `start.py` wires everything together |
| `utils/` | nothing project-internal | `human_size()`, `sha256()` |
| `types/` | nothing project-internal | `SyncTask`, `Status` |
| `config.py` | database.py only | `Settings`, `_apply_db_overrides()` |
| `database.py` | nothing | `Database`, `FileRecord`, `EventRecord` |

## Key Conventions

### Code Style

- `# pyright: reportCallInDefaultInitializer=false` at top of CLI command files (Typer hack)
- `from __future__ import annotations` in every file
- All `@staticmethod` for pure functions; constructor injection for services
- Type annotations everywhere (basedpyright strict with some reports disabled)
- Private helpers prefixed with `_` (e.g. `_apply_db_overrides`)
- Imports: stdlib → third-party → project, separated by blank line
- Async for DB and rclone upload; sync for aria2 (blocking API)

### Adding a New CLI Command

1. Create `src/hf_sync/cli/commands/<name>.py`
2. Decorate function with `@app.command()`
3. Import in `src/hf_sync/cli/commands/__init__.py`
4. Update docstring in `src/hf_sync/cli/__init__.py`
5. Add tests in `tests/test_cli.py`

### Database

- Two tables: `files` (sync state) and `events` (audit log) + `config` (key-value)
- All raw SQL in `repositories/files.py` (not in models/database)
- Status flow: PENDING → DOWNLOADING → UPLOADING → VERIFYING → DONE | FAILED
- Config stored in DB `config` table, overrides .env defaults at startup

### Tests

- 100% coverage required. Run: `uv run python -m pytest tests/ --cov=src/hf_sync --tb=short -q`
- Typecheck: `uv run basedpyright src/hf_sync/ tests/` — 0 errors required
- CLI commands tested via `typer.testing.CliRunner` with mocking
- Async commands tested with `pytest-asyncio` (`asyncio_mode = "auto"`)
- Use `from unittest.mock import AsyncMock, MagicMock, patch`
- Tests live in `tests/` directory, one file per module
- No conftest.py — fixtures defined inline or imported directly
- Pattern: mock external services, test all paths (success, failure, edge cases)

### Git & Releases

- Commits follow [Conventional Commits](https://www.conventionalcommits.org/):
  `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `ci:`, `test:`, `perf:`
- Branches: `main` (releases), `dev` (development)
- PRs from `dev` → `main`, squash merge
- `python-semantic-release` auto-bumps version and creates GitHub Release on push to `main`
- Release provides `.tar.gz` + `.whl` assets

### Development Commands

```sh
uv sync                  # install deps + dev deps
uv sync --group dev      # install dev deps only
uv run python -m pytest tests/ --cov=src/hf_sync --tb=short -q  # test
uv run basedpyright src/hf_sync/ tests/                         # typecheck
uv run ruff check src/hf_sync/ tests/                           # lint
uv run hf-sync --help    # run locally
uv build                 # build distribution
```

### Dependencies

- `uv` for package management (not pip)
- `typer` for CLI (not argparse)
- `rich` for terminal UI (Progress, Live, Table)
- `aiosqlite` for async SQLite
- `httpx` for HTTP (aria2 RPC, GitHub API)
- `loguru` for logging
- `pydantic-settings` for config loading
- `huggingface-hub` for HF API
- `orjson` for fast JSON (optional utility)
- `sqlmodel` for table definitions

### Rclone Upload Progress

Async rclone uses `--stats=1s` flag, parses stderr with regex for pct/speed.
Progress callback signature: `(stage: str, pct: float, speed: str) → None`.

### Aria2 Download Progress

Polling-based. `aria2.tellStatus(gid)` returns `completedLength`, `totalLength`, `downloadSpeed`.
Progress callback: `(completed_bytes: int, total_bytes: int, speed_bps: int) → None`.
