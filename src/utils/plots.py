from pathlib import Path
from typing import Dict

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from ..agents.schemas import MetricsBundle, MetricSeries


METRIC_CONFIG: Dict[str, Dict[str, str]] = {
    "case_growth": {
        "title": "Crescimento Mensal de Casos de SRAG",
        "ylabel": "Variação Percentual (%)",
        "y_col": "taxa_aumento_pct",
        "x_col": "date_month",
    },
    "mortality_rate": {
        "title": "Taxa de Mortalidade Mensal por SRAG",
        "ylabel": "Mortalidade (%)",
        "y_col": "taxa_mortalidade_pct",
        "x_col": "date_month",
    },
    "uti_utilization_rate": {
        "title": "Taxa de Ocupação de UTI por SRAG",
        "ylabel": "Ocupação de UTI (%)",
        "y_col": "taxa_ocupacao_uti_pct",
        "x_col": "date_month",
    },
    "vaccination_rate": {
        "title": "Cobertura Vacinal (COVID-19) em Casos de SRAG",
        "ylabel": "Cobertura Vacinal (%)",
        "y_col": "taxa_vacinacao_casos_pct",
        "x_col": "date_month",
    },
    "daily_cases": {
        "title": "Quantiade de casos diário de SRAG - Últimos 30 dias",
        "ylabel": "Quantidade de casos",
        "y_col": "casos_diarios",
        "x_col": "data",
    },
    "monthly_cases": {
        "title": "Quantiade de casos por mês de SRAG - Últimos 12 meses",
        "ylabel": "Quantidade de casos",
        "y_col": "casos_mensais",
        "x_col": "date_month",
    },
}


def _plot_single_metric(
    df: pd.DataFrame, config: Dict[str, str], output_path: Path, plot_type: str
) -> None:
    """Plots a single metric as a line or bar chart and saves the output.

    This is a helper function that generates a matplotlib plot based on the provided data and configuration.
    It handles empty dataframes, creates the plot (either a line or bar chart),
    applies standard formatting, and saves the resulting image in both PNG and SVG formats.

    Args:
        df (pd.DataFrame): The DataFrame containing the data to be plotted.
        config (Dict[str, str]): A dictionary with configuration details like plot title, axis labels, and column names.
        output_path (Path): The Path object specifying where the plot image should be saved.
        plot_type (str): The type of plot to generate, either 'line' or 'bar'.

    Returns:
        None: This function saves files but does not return any value.
    """
    if df.empty:
        print(f"[AVISO] Nenhum dado para plotar para o gráfico: {config['title']}")
        return

    df = df.sort_values(by=config["x_col"])

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(11, 6))

    if plot_type == "line":
        ax.plot(
            df[config["x_col"]],
            df[config["y_col"]],
            marker="o",
            linestyle="-",
            color="#00529B",
            label="Valor Mensal",
        )
    elif plot_type == "bar":
        ax.bar(
            df[config["x_col"]],
            df[config["y_col"]],
            color="#4f87ff",
            width=0.8,
            label="Valor Mensal",
        )

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{y:.1f}%"))
    ax.set_title(config["title"], fontsize=16, weight="bold", pad=20)
    ax.set_ylabel(config["ylabel"], fontsize=12)
    if config["x_col"] == "data":
        ax.set_xlabel("Data", fontsize=12)
    else:
        ax.set_xlabel("Mês/Ano", fontsize=12)

    ax.tick_params(axis="x", rotation=45)
    ax.grid(True, which="major", linestyle="--", linewidth="0.5", color="grey")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    fig.savefig(output_path.with_suffix(".svg"))
    plt.close(fig)


def plot_static_metrics(
    bundle: MetricsBundle, output_dir: str | Path, plot_type: str = "line"
) -> None:
    """Generates and saves plots for each metric in a MetricsBundle object.

    This function iterates through a predefined set of metric configurations,
    extracts the corresponding data from a `MetricsBundle`, and then uses a
    helper function to generate and save each plot to a specified directory.

    Args:
        bundle (MetricsBundle): The object containing the metric data to be plotted.
        output_dir (str | Path): The destination directory where the plot images (PNG and SVG) will be saved.
        plot_type (str, optional): The type of plot to generate. Must be 'line' or 'bar'. Defaults to 'line'.

    Returns:
        None: This function does not return a value; it saves the plot files as a side effect.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Validação do tipo de plot
    if plot_type not in ["line", "bar"]:
        raise ValueError(
            f"Tipo de gráfico inválido: '{plot_type}'. Escolha entre 'line' ou 'bar'."
        )

    print(
        f"Gerando gráficos do tipo '{plot_type}' no diretório: {output_path.absolute()}"
    )

    for metric_name, config in METRIC_CONFIG.items():
        metric_series: MetricSeries = getattr(bundle, metric_name)
        df = pd.DataFrame(metric_series.rows)
        plot_filename = (
            output_path / f"{metric_name}_{plot_type}.png"
        )  # Adiciona o tipo ao nome do arquivo

        # Passa o 'plot_type' para a função auxiliar
        _plot_single_metric(df, config, plot_filename, plot_type)

    print("Gráficos gerados com sucesso!")
