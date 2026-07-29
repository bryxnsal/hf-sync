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

_REPO = "bryxnsal/hf-sync"
_GIT_REPO = f"https://github.com/{_REPO}.git"


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
            f"https://api.github.com/repos/{_REPO}/releases/latest",
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

    # Dev build → install stable (even if release segment is ahead)
    if current_v.is_prerelease:
        if current_v.release == latest_v.release:
            console.print(f"[green]✓ Already at {latest_version} (dev build)[/green]")
            return
        console.print(
            f"[yellow]⚠ Dev build ({current}) → installing stable ({latest_version})[/yellow]"
        )
    elif current_v >= latest_v:
        console.print("[green]✓ Already up to date[/green]")
        return

    console.print(f"[yellow]Updating to {latest_version}...[/yellow]")

    git_url = f"{_GIT_REPO}@{latest_tag}"

    try:
        subprocess.run(
            ["uv", "tool", "install", "--from", git_url, "hf-sync", "--upgrade"],
            check=True,
            capture_output=False,
        )
    except FileNotFoundError:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", f"git+{git_url}"],
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
