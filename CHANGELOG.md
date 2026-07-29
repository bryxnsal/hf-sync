# CHANGELOG


## v0.4.2 (2026-07-29)

### Bug Fixes

- **install**: Install from release artifact instead of git clone
  ([#10](https://github.com/bryxnsal/hf-sync/pull/10),
  [`56d4e6d`](https://github.com/bryxnsal/hf-sync/commit/56d4e6d2a264efc147d27a14f2566e33632f63d0))

Instead of cloning the repo (which generates dev versions like 0.4.1.dev1 from setuptools-scm),
  download the .tar.gz from the latest GitHub Release and install from that file. This ensures the
  installed version matches the release tag exactly.

- update.py: download release asset .tar.gz, install via uv/pip - install.sh: fetch latest release
  from GitHub API, download artifact - tests: rewrite to match new install-paths (tempfile tarball,
  httpx side_effect)


## v0.4.1 (2026-07-29)

### Bug Fixes

- **update**: Detect dev builds ahead of latest release
  ([#9](https://github.com/bryxnsal/hf-sync/pull/9),
  [`ac9c782`](https://github.com/bryxnsal/hf-sync/commit/ac9c78242ccfbc2057690ce78510f892f966847a))

### Documentation

- Add uninstall section to README
  ([`1a41c28`](https://github.com/bryxnsal/hf-sync/commit/1a41c28d2b4040bfa047edfb1d317a77b0b7f9a4))


## v0.4.0 (2026-07-29)

### Features

- Add uninstall.sh script ([#8](https://github.com/bryxnsal/hf-sync/pull/8),
  [`6e6a76b`](https://github.com/bryxnsal/hf-sync/commit/6e6a76ba29a749fe60611b5a6723a90b27441f7c))


## v0.3.0 (2026-07-29)

### Features

- **install**: Show version info during install/update
  ([#7](https://github.com/bryxnsal/hf-sync/pull/7),
  [`d2e8c70`](https://github.com/bryxnsal/hf-sync/commit/d2e8c705cff04a4d6488d3450862bfb3dd38d6a8))

install.sh now shows: Current: X.X.X → New: Y.Y.Y (when updating)

Version: Y.Y.Y (fresh install)


## v0.2.4 (2026-07-29)

### Bug Fixes

- **version**: Use setuptools-scm to derive version from git tags
  ([#6](https://github.com/bryxnsal/hf-sync/pull/6),
  [`5acc0e7`](https://github.com/bryxnsal/hf-sync/commit/5acc0e7ed89da8a76ec22df4aa1a5605905e0f9e))

Remove _version.py, version_variable. Remove reliance on manual version bumps that never worked
  (semantic-release tags but doesn't update files). Version now always correct at build time from
  git tag.

app.py and update.py use importlib.metadata.version() which reads from installed package metadata
  (correct after scm build).


## v0.2.3 (2026-07-29)

### Bug Fixes

- **version**: Move version to _version.py, use setuptools dynamic attr
  ([#5](https://github.com/bryxnsal/hf-sync/pull/5),
  [`5ecef9c`](https://github.com/bryxnsal/hf-sync/commit/5ecef9ce20d8fd0b09d30477979157f8e597e0d2))

Root cause: pyproject.toml version never bumped by semantic-release (squash merges from dev
  overwrite release commits).

Fix: - Create src/hf_sync/_version.py with __version__ - pyproject.toml: use dynamic = ["version"]
  with attr pointer - semantic-release version_variable points to _version.py - app.py and update.py
  import __version__ directly - Tests patched accordingly


## v0.2.2 (2026-07-29)

### Bug Fixes

- **install**: Detect existing install, show 'updated' vs 'installed'
  ([#4](https://github.com/bryxnsal/hf-sync/pull/4),
  [`9c8bc79`](https://github.com/bryxnsal/hf-sync/commit/9c8bc791214bc8fdb0468a0dc18199ab681e7658))


## v0.2.1 (2026-07-29)

### Bug Fixes

- **update**: Use git URL for uv/pip upgrade instead of local path
  ([#3](https://github.com/bryxnsal/hf-sync/pull/3),
  [`61e44a2`](https://github.com/bryxnsal/hf-sync/commit/61e44a24e32039cfc80990da12f0ec96499badc2))

uv tool upgrade hf-sync fails when package installed from local path. Fix uses: uv tool install
  --from <repo-url> hf-sync --upgrade. Pip fallback also uses git+URL instead of bare package name.


## v0.2.0 (2026-07-29)

### Features

- **cli**: Add --version/-v flag and -h short flag
  ([#2](https://github.com/bryxnsal/hf-sync/pull/2),
  [`a1b15e8`](https://github.com/bryxnsal/hf-sync/commit/a1b15e83516fa4a02773ded8777f64cd4b5a6bb6))

* feat(cli): add hf-sync update command

Checks latest version via GitHub API and upgrades via uv or pip.

* docs: add CLAUDE.md for AI agent guidance

* feat(cli): add --version / -v flag

Use @app.callback with invoke_without_command=True to show help when no subcommand given. Eager
  version callback exits before command dispatch.

* feat(cli): add -h short flag for --help


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
