"""Update command — upgrade hf-sync to latest version."""
# pyright: reportCallInDefaultInitializer=false
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from importlib.metadata import version as pkg_version

import httpx
import typer
from packaging.version import Version

from hf_sync.cli.app import app, console

_REPO = "bryxnsal/hf-sync"


def _parse_tag(tag: str) -> Version:
    """Parse PEP 440 version string."""
    return Version(tag.removeprefix("v"))


def _asset_url(data: dict) -> str | None:
    """Get .tar.gz download URL from release data."""
    for asset in data.get("assets", []):
        name: str = asset["name"]
        if name.endswith(".tar.gz"):
            return asset["browser_download_url"]
    return None


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

    # Get release asset URL
    url = _asset_url(data)
    if not url:
        console.print("[red]✗ No .tar.gz asset found in latest release[/red]")
        raise typer.Exit(1)

    console.print("[yellow]Downloading release...[/yellow]")

    try:
        resp = httpx.get(url, timeout=120)
        resp.raise_for_status()
    except Exception as e:
        console.print(f"[red]✗ Failed to download release: {e}[/red]")
        raise typer.Exit(1) from e

    # Write to temp file and install
    tmp = tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False)
    try:
        tmp.write(resp.content)
        tmp.close()

        console.print("[yellow]Installing...[/yellow]")

        try:
            subprocess.run(
                ["uv", "tool", "install", "--reinstall", tmp.name],
                check=True,
                capture_output=False,
            )
        except FileNotFoundError:
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", tmp.name],
                    check=True,
                    capture_output=False,
                )
            except subprocess.CalledProcessError as e:
                console.print(f"[red]✗ pip upgrade failed: {e}[/red]")
                raise typer.Exit(1) from e
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗ uv upgrade failed: {e}[/red]")
            raise typer.Exit(1) from e
    finally:
        os.unlink(tmp.name)

    console.print(f"[green]✓ Updated to {latest_version}![/green]")
    console.print("  Restart hf-sync to use new version.")
