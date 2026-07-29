"""Update command — upgrade hf-sync to latest version."""
# pyright: reportCallInDefaultInitializer=false
from __future__ import annotations

import subprocess
import sys
from importlib.metadata import version as pkg_version

import httpx
import typer
from packaging.version import Version

from hf_sync.cli.app import app, console

_REPO = "https://github.com/bryxnsal/hf-sync.git"


def _parse_tag(tag: str) -> Version:
    """Parse PEP 440 version string."""
    return Version(tag.removeprefix("v"))


@app.command()
def update() -> None:
    """Update hf-sync to the latest version."""
    current = pkg_version("hf-sync")
    console.print(f"Current version: [bold]{current}[/bold]")

    # Fetch latest release from GitHub
    try:
        resp = httpx.get(
            "https://api.github.com/repos/bryxnsal/hf-sync/releases/latest",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        latest_tag: str = data["tag_name"]
        latest_version = latest_tag.removeprefix("v")
    except Exception as e:
        console.print(f"[red]✗ Failed to check latest version: {e}[/red]")
        raise typer.Exit(1) from e

    console.print(f"Latest version:  [bold]{latest_version}[/bold]")

    current_v = _parse_tag(current)
    latest_v = _parse_tag(latest_version)

    if current_v > latest_v and current_v.is_prerelease:
        console.print(
            f"[yellow]⚠ Dev build ({current}) — ahead of latest release ({latest_version})[/yellow]"
        )
        return

    if current_v >= latest_v:
        console.print("[green]✓ Already up to date[/green]")
        return

    console.print("[yellow]Updating...[/yellow]")

    try:
        # Try uv tool install --from <repo> --upgrade
        subprocess.run(
            ["uv", "tool", "install", "--from", _REPO, "hf-sync", "--upgrade"],
            check=True,
            capture_output=False,
        )
    except FileNotFoundError:
        # Fallback to pip install from git repo
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    f"git+{_REPO}",
                ],
                check=True,
                capture_output=False,
            )
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗ pip upgrade failed: {e}[/red]")
            raise typer.Exit(1) from e
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ uv upgrade failed: {e}[/red]")
        raise typer.Exit(1) from e

    console.print(f"[green]✓ Updated to {latest_version}![/green]")
    console.print("  Restart hf-sync to use new version.")
