"""Leakprint CLI."""

from pathlib import Path

import typer

from leakprint import __version__
from leakprint.pipeline import run_pipeline

app = typer.Typer(
    name="leakprint",
    help="Blueprint + Risk Register for smart homes.",
)


def _path_callback(value: str | None) -> Path | None:
    return Path(value) if value else None


@app.command()
def run(
    inventory: Path = typer.Option(
        None,
        "--inventory",
        "-i",
        path_type=Path,
        help="Path to inventory CSV",
    ),
    from_ha: bool = typer.Option(
        False,
        "--from-ha",
        help="Ingest from Home Assistant (uses HASS_URL, HASS_TOKEN)",
    ),
    out: Path = typer.Option(
        Path("artifacts"),
        "--out",
        "-o",
        path_type=Path,
        help="Output directory for artifacts",
    ),
    cache: Path = typer.Option(
        Path("cache"),
        "--cache",
        "-c",
        path_type=Path,
        help="Cache directory",
    ),
    max_nvd_results: int = typer.Option(
        20,
        "--max-nvd-results",
        help="Max CVE results per device from NVD",
    ),
    kev_ttl_hours: int = typer.Option(
        24,
        "--kev-ttl-hours",
        help="KEV cache TTL in hours",
    ),
) -> None:
    """Run full pipeline: ingest → enrich → score → report."""
    run_pipeline(
        inventory_path=inventory,
        from_ha=from_ha,
        out_dir=out,
        cache_dir=cache,
        max_nvd_results=max_nvd_results,
        kev_ttl_hours=kev_ttl_hours,
    )


@app.command()
def ingest(
    inventory: Path = typer.Option(
        None,
        "--inventory",
        "-i",
        path_type=Path,
        help="Path to inventory CSV",
    ),
    from_ha: bool = typer.Option(
        False,
        "--from-ha",
        help="Ingest from Home Assistant",
    ),
    out: Path = typer.Option(
        Path("artifacts"),
        "--out",
        "-o",
        path_type=Path,
        help="Output directory",
    ),
) -> None:
    """Ingest inventory from CSV or Home Assistant."""
    from leakprint.pipeline import ingest_only

    ingest_only(
        inventory_path=inventory,
        from_ha=from_ha,
        out_dir=out,
    )


@app.command()
def enrich(
    out: Path = typer.Option(
        Path("artifacts"),
        "--out",
        "-o",
        path_type=Path,
        help="Output directory",
    ),
    cache: Path = typer.Option(
        Path("cache"),
        "--cache",
        "-c",
        path_type=Path,
        help="Cache directory",
    ),
    max_nvd_results: int = typer.Option(
        20,
        "--max-nvd-results",
        help="Max CVE results per device",
    ),
    kev_ttl_hours: int = typer.Option(
        24,
        "--kev-ttl-hours",
        help="KEV cache TTL in hours",
    ),
) -> None:
    """Enrich inventory with KEV and NVD data."""
    from leakprint.pipeline import enrich_only

    enrich_only(
        out_dir=out,
        cache_dir=cache,
        max_nvd_results=max_nvd_results,
        kev_ttl_hours=kev_ttl_hours,
    )


@app.command()
def score(
    out: Path = typer.Option(
        Path("artifacts"),
        "--out",
        "-o",
        path_type=Path,
        help="Output directory",
    ),
) -> None:
    """Score devices and produce risk register."""
    from leakprint.pipeline import score_only

    score_only(out_dir=out)


@app.command()
def report(
    out: Path = typer.Option(
        Path("artifacts"),
        "--out",
        "-o",
        path_type=Path,
        help="Output directory",
    ),
) -> None:
    """Generate report artifacts from scored data."""
    from leakprint.pipeline import report_only

    report_only(out_dir=out)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version",
    ),
) -> None:
    if version:
        typer.echo(f"leakprint {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo("Run 'leakprint run --help' or 'leakprint ingest --help' for usage.")


if __name__ == "__main__":
    app()
