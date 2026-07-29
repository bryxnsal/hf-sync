"""Update command — upgrade hf-sync to latest version."""
# pyright: reportCallInDefaultInitializer=false
from __future__ import annotations

import re
import subprocess
import sys
from importlib.metadata import version as pkg_version

import httpx
import typer

from hf_sync.cli.app import app, console


def _parse_tag(tag: str) -> tuple[int, ...]:
    """Parse 'v1.2.3' → (1,2,3) for comparison."""
    m = re.match(r"v?(\d+(?:\.\d+)*)", tag)
    return tuple(int(x) for x in m.group(1).split(".")) if m else (0,)


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

    if _parse_tag(latest_version) <= _parse_tag(current):
        console.print("[green]✓ Already up to date[/green]")
        return

    console.print("[yellow]Updating...[/yellow]")

    try:
        # Try uv tool upgrade first
        subprocess.run(
            ["uv", "tool", "upgrade", "hf-sync"],
            check=True,
            capture_output=False,
        )
    except FileNotFoundError:
        # Fallback to pip
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    "hf-sync",
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
