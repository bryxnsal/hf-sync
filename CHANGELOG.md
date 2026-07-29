# CHANGELOG


## v0.1.0 (2026-07-29)

### Bug Fixes

- Ensure DB and temp directories exist before use
  ([`3fc232f`](https://github.com/bryxnsal/hf-sync/commit/3fc232f6bc76d0f5dfe726f287b1f0c2fffa897c))

Connect and init_db now create parent directory for state.db. _start_impl creates temp_dir before
  running pipeline. Fixes 'unable to open database file' on fresh installs.

- Freeze live display rebuilds via live.update()
  ([`3607a36`](https://github.com/bryxnsal/hf-sync/commit/3607a364651240d297bea82484d10f9efdd960ce))

build_display() was called once at Live() construction, creating static Group that never re-reads
  completed_lines changes.

Fix: capture live handle via 'as live:' and call live.update(build_display()) after each file
  completes.

Add tests: _FrozenBar renderable, _fmt_elapsed, color codes.

- **doctor**: Use aria2.getVersion for connectivity check
  ([`926303e`](https://github.com/bryxnsal/hf-sync/commit/926303e73de9423f01e3abe72df6cc691b0c4173))

tell_status with fake GID fails because the GID doesn't exist, making doctor falsely report aria2 as
  down. Use getVersion instead, which only requires RPC to be reachable.

- **doctor): fallback 127.0.0.1, not-configured state, dry-run mode; feat(pipeline**: Download
  speed, summary table, cancel handler
  ([`46be565`](https://github.com/bryxnsal/hf-sync/commit/46be5655443c65b926e3e9a613e6be28c3a0e53c))

- **release**: Use pip build instead of uv in semantic-release container
  ([#1](https://github.com/bryxnsal/hf-sync/pull/1),
  [`65dbc38`](https://github.com/bryxnsal/hf-sync/commit/65dbc386ee074f2dc61deecb1034ec5d17b92997))

uv not available inside python-semantic-release Docker container. Change build_command to pip
  install build + python -m build.

### Chores

- 100% coverage, 0 type warnings, clean up test type issues
  ([`e91ab20`](https://github.com/bryxnsal/hf-sync/commit/e91ab204fdda3c4ccf3377bb0ea3759680ca9543))

- Add missing type annotations to test fixtures and mock params - Remove unused imports across test
  files - Suppress noise rules for test-specific patterns - Fix pydantic-settings stub compatibility
  for _env_file - Fix tmp_path type annotation (Path not object) - Fix pending_files type to allow
  None append - Fix Verifier class attribute initialization - Fix logger._core private attribute
  access - Fix __main__ import to use cli module directly - Add progress callback type alias for
  type safety - Add reportMissingParameterType/unusedParameter/Variable suppression - Achieve 100%
  coverage (1058/1058 lines, 252 tests)

### Continuous Integration

- Add GitHub Actions workflows and install.sh
  ([`c539720`](https://github.com/bryxnsal/hf-sync/commit/c5397207859fb5220563af81a2d10be1a70096f2))

- Add CI workflow (typecheck + tests on push/PR) - Add Release workflow with python-semantic-release
  v9 - Auto-bump version from conventional commits - Auto-generate CHANGELOG.md - Auto-create GitHub
  Release with sdist + wheel - Trigger: push to main or manual dispatch - Add install.sh one-liner
  (uv tool install or pip fallback) - Add python-semantic-release dev dependency - Configure
  [tool.semantic_release] in pyproject.toml - Add .coverage and *.log to .gitignore - Update project
  URLs to point to bryxnsal/hf-sync

### Documentation

- Add one-liner install to README
  ([`a543df6`](https://github.com/bryxnsal/hf-sync/commit/a543df6db7af897af34f65ec3a6d6f01dd174476))

### Features

- Add interactive config command, store settings in DB instead of .env
  ([`1e5bcb9`](https://github.com/bryxnsal/hf-sync/commit/1e5bcb917eabda52b800a12bc9d1d35688fecacd))

- Add hf-sync config command with interactive prompts for each setting - Store settings in DB config
  table instead of .env file - Generalize DB fallback for all settings at startup - Add
  validate_token() to HuggingFaceService - Remove _CONFIG_PATH and os import from cli.py - Update
  README with new config flow - 100% test coverage

- Async rclone upload with real-time progress
  ([`f83c5eb`](https://github.com/bryxnsal/hf-sync/commit/f83c5eb150febf1e67ebd1c35330fd00e829ad39))

Replace sync subprocess.run for rclone copyto with async create_subprocess_exec that parses
  --stats=1s stderr output. Live display no longer blocks during upload — timer, bar, and speed
  update in real time.

- Clean Live display, cleanup on failure, resume interrupted states
  ([`78ba1db`](https://github.com/bryxnsal/hf-sync/commit/78ba1db8df4160f16feffb73244aa0965d9dcf82))

- Suppress loguru console output during sync (redirect to file) - Replace Progress spinner with Rich
  Live display showing: completed files, current file bar (color-coded), overall progress - Download
  green, upload blue, verify yellow - Clean up temp files when download/upload/verify fails - Resume
  now resets FAILED + DOWNLOADING + UPLOADING + VERIFYING to PENDING and removes orphaned temp files

- Frozen completed-file history, remove overall bar, capture error messages
  ([`1946f9a`](https://github.com/bryxnsal/hf-sync/commit/1946f9a5dbfed2371f7fbb46dbf057791eff230f))

- coordinator.run() now returns (bool, str) to pass error message to UI - cli.py: add _FrozenBar
  renderable that shows ✓/✗ filename (size) ━━━━━━━━━━━━━━━━ 100% MM:SS OK as a single frozen line
  per file - Replace completed_lines list[Text] with list[_FrozenBar]; 10-line history - Remove
  overall_progress bar — user wants cleaner display - Capture start/elapsed time per file for frozen
  bar timestamp

- **start**: Auto-init DB when no files are pending
  ([`4d5b241`](https://github.com/bryxnsal/hf-sync/commit/4d5b241132de78aa93d9b7dfd5765328ff7d3225))

Start now scans the repo and populates pending files if the DB is empty, instead of immediately
  saying 'Pipeline complete'.

### Refactoring

- **cli**: Split monolithic cli.py into modular package
  ([`c0722e0`](https://github.com/bryxnsal/hf-sync/commit/c0722e0b5f56dc18ca36d56823356ac605cadfdb))

Break 575-line cli.py into cli/ package with separate modules per responsibility:

- cli/app.py: standalone app/console instances - cli/shared/display.py: _FrozenBar, _fmt_elapsed,
  _parse_destination, _show_dry_run - cli/commands/auth.py: auth command - cli/commands/config.py:
  config command - cli/commands/doctor.py: doctor command - cli/commands/init.py: init command +
  _init_impl - cli/commands/start.py: start command + _start_impl - cli/commands/resume.py: resume
  command + _resume_impl - cli/commands/verify.py: verify command + _verify_impl - cli/__init__.py:
  main(), __all__ exports, side-effect command registration

Test imports/patch paths updated to match new module locations. pyproject.toml: add
  reportUnusedImport/Function/Class suppressions.
