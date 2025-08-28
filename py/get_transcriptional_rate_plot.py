#!/usr/bin/env python3
from pathlib import Path

import pandas as pd
import typer
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import plotly.io as pio
pio.kaleido.scope.mathjax = None

app = typer.Typer(add_completion=False, no_args_is_help=True)

def chunk(items: list, size: int) -> list[list]:
    return [items[i:i+size] for i in range(0, len(items), size)]

@app.command(help="Histogram subplots (≤3 per subplot), sorted by ascending mean, with per-subplot legends.")
def main(
    log: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="BEAST 2 log file (TSV)."),
    output: Path = typer.Argument(..., help="Output file (.html for interactive; .png/.pdf/.svg needs kaleido)."),
    burnin: float = typer.Option(0.0, help="Burn-in proportion (must be a value between 0 and 1)."),
    bins: int = typer.Option(50, help="Number of histogram bins."),
    title: str = typer.Option("", help="Overall figure title."),
    font_family: str = typer.Option("Georgia Pro", help="Layout font family."),
    font_size: int = typer.Option(16, help="Base font size."),
    show: bool = typer.Option(True, help="Show the figure in a browser (interactive)."),
    skip_lines: int = typer.Option(0, help="Skip this many header lines before parsing (like tail -n +{N+1})."),
    draw_means: bool = typer.Option(False, help="Draw a dashed vertical line for each rate mean in each subplot."),
):
    # --- Load ---
    df = pd.read_csv(log, sep="\t", comment="#", skiprows=skip_lines if skip_lines > 0 else None)
    burnin_count = int(burnin*len(df.index))
    # print(burnin)
    df = df.truncate(before=burnin_count)

    rate_names_by_id: dict[str, str] = {
        "IntAssim_rate": "Internal assimilation",
        "ExtAssim_rate": "External assimilation",
        "Harm_rate": "Harmonization",
        "Sem_rate": "Semantic change",
        "Prag_rate": "Pragmatic change",
        "Idio_rate": "Idiolectal change",
        "AurConf_rate": "Aural confusion",
        "Ditt_rate": "Dittography",
        "Lipo_rate": "Lipography",
        "HomArcLetter_rate": "Homoioarcton (letter)",
        "HomArcPart_rate": "Homoioarcton (part)",
        "HomArcWord_rate": "Homoioarcton (word)",
        "HomTelLetter_rate": "Homoioteleuton (letter)",
        "HomTelPart_rate": "Homoioteleuton (part)",
        "HomTelWord_rate": "Homoioteleuton (word)",
        "PalConf_rate": "Paleographic confusion",
        "Byz_rate": "Byzantine assimilation",
    }

    # Collect present (key, pretty, series, mean)
    present: list[tuple[str, str, pd.Series, float]] = []
    for key, pretty in rate_names_by_id.items():
        if key in df.columns:
            s = df[key].dropna()
            if not s.empty:
                present.append((key, pretty, s, float(s.mean())))

    if not present:
        typer.secho("None of the mapped rate columns were found in the file.", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    # Sort by ascending mean and group into sublists of up to 3 (max 6 subplots)
    present.sort(key=lambda t: t[3])
    groups: list[list[tuple[str, str, pd.Series, float]]] = chunk(present, 3)[:6]
    nrows = len(groups)

    # Build figure (independent scales, no subplot titles)
    fig = make_subplots(
        rows=nrows,
        cols=1,
        shared_xaxes=False,
        shared_yaxes=False,
        vertical_spacing=0.025,  # tighter spacing
    )

    # Same 3 colorblind-safe colors for every subplot (Okabe–Ito)
    base_colors: list[str] = ["#0072B2", "#D55E00", "#009E73"]  # blue, vermillion, green

    def add_histograms(items: list[tuple[str, str, pd.Series, float]], row: int) -> None:
        # assign colors per position (reused for each subplot)
        colors = base_colors[:len(items)]

        # add histograms + optional mean lines
        for i, (key, pretty, series, mu) in enumerate(items):
            fig.add_trace(
                go.Histogram(
                    x=series,
                    name=pretty,
                    nbinsx=bins,
                    histnorm="probability density",
                    opacity=0.60,
                    marker_color=colors[i],
                    showlegend=False,  # we'll add per-subplot legend via annotations
                ),
                row=row, col=1
            )
            if draw_means:
                fig.add_vline(
                    x=mu,
                    line_dash="dash",
                    line_width=1,
                    line_color=colors[i],
                    row=row, col=1
                )

        # x-range: central 95% for each series, then union across the subplot
        qmins = [float(s.quantile(0.025)) for _, _, s, _ in items]
        qmaxs = [float(s.quantile(0.975)) for _, _, s, _ in items]
        xmin = min(qmins)
        xmax = max(qmaxs)
        fig.update_xaxes(range=[xmin, xmax], row=row, col=1)

        # per-subplot legend using colored squares (one annotation per entry)
        # place near top-right of the plotting area
        # positions stepped downward so they don't overlap
        for i, (_, pretty, _, _) in enumerate(items):
            fig.add_annotation(
                x=0.98, y=0.98 - i * 0.14,  # tweak spacing if needed
                xref=f"x{'' if row == 1 else row} domain",
                yref=f"y{'' if row == 1 else row} domain",
                text=f"<b>■</b> {pretty}",
                showarrow=False,
                align="right",
                font=dict(size=20, color=colors[i]),
                bgcolor="white",
                # bordercolor="rgba(0,0,0,0.15)",
                borderwidth=0,
                borderpad=2,
            )

    # Build rows
    for r, grp in enumerate(groups, start=1):
        add_histograms(grp, row=r)

    # Layout
    fig.update_layout(
        title=title,
        barmode="overlay",
        font=dict(family=font_family, size=font_size),
        width=1200,
        height=300 * nrows,
        margin=dict(l=60, r=30, t=70, b=60),
        showlegend=False,  # no global legend
        plot_bgcolor="white",
        title_font_color="black",
    )

    gridcolor = "#dddddd"
    fig.update_xaxes(gridcolor=gridcolor)
    fig.update_yaxes(gridcolor=gridcolor)

    fig.update_xaxes(showline=True, linewidth=1, linecolor='black', mirror=True, ticks='outside')
    fig.update_yaxes(showline=True, linewidth=1, linecolor='black', mirror=True, ticks='outside')

    # Axes labels: y on each row; x only on bottom row
    for r in range(1, nrows + 1):
        fig.update_yaxes(title_text="Density", row=r, col=1)
        fig.update_xaxes(title_text="", row=r, col=1)
    fig.update_xaxes(title_text="Rate (relative to unexplained changes)", row=nrows, col=1)

    # Remove margins
    fig.update_layout(
        margin=dict(l=30, r=0, t=0, b=30)
    )

    # --- Save ---
    suffix = output.suffix.lower()
    if suffix == ".html":
        fig.write_html(str(output), include_plotlyjs="cdn", full_html=True)
    else:
        try:
            # Requires: pip install -U kaleido
            fig.write_image(str(output))
        except Exception as e:
            typer.secho(
                f"Failed to export static image ({output.suffix}). "
                f"Install 'kaleido' or export to .html instead.\nError: {e}",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(1)

    # Print subplot order (by keys)
    typer.echo("Subplot order (by keys):")
    for idx, grp in enumerate(groups, start=1):
        typer.echo(f"  Row {idx}: {', '.join(k for k, _, _, _ in grp)}")

    typer.secho(f"Saved to {output}", fg=typer.colors.GREEN)

    if show:
        fig.show("browser")

if __name__ == "__main__":
    app()
