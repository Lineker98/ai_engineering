import sqlite3
from pathlib import Path
from typing import Optional, Dict

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from .helper_functions import save_chart_data
import matplotlib.ticker as mticker
from ..agents.schemas import MetricsBundle, MetricSeries


METRIC_CONFIG: Dict[str, Dict[str, str]] = {
    'case_growth': {
        'title': 'Crescimento Mensal de Casos de SRAG',
        'ylabel': 'Variação Percentual (%)',
        'y_col': 'taxa_aumento_pct',
        'x_col': 'date_month',
    },
    'mortality_rate': {
        'title': 'Taxa de Mortalidade Mensal por SRAG',
        'ylabel': 'Mortalidade (%)',
        'y_col': 'taxa_mortalidade_pct',
        'x_col': 'date_month',
    },
    'uti_utilization_rate': {
        'title': 'Taxa de Ocupação de UTI por SRAG',
        'ylabel': 'Ocupação de UTI (%)',
        'y_col': 'taxa_ocupacao_uti_pct',
        'x_col': 'date_month',
    },
    'vaccination_rate': {
        'title': 'Cobertura Vacinal (COVID-19) em Casos de SRAG',
        'ylabel': 'Cobertura Vacinal (%)',
        'y_col': 'taxa_vacinacao_casos_pct',
        'x_col': 'date_month',
    }
}


def fetch_dates_df(
    db_path: str | Path,
    table: str,
    date_col: str,
    where_clause: Optional[str] = None,
    ) -> pd.DataFrame:
    
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"SQLite não encontrado em: {path.resolve()}")

    where = f"WHERE {where_clause}" if where_clause else ""
    sql = f"""
        SELECT {date_col} AS dt
        FROM {table}
        {where}
        AND {date_col} IS NOT NULL
    """.replace("WHERE  AND", "WHERE ")

    with sqlite3.connect(str(path)) as conn:
        df = pd.read_sql(sql, conn)
    
    df["dt"] = pd.to_datetime(df["dt"], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["dt"]).sort_values("dt").reset_index(drop=True)
    return df

def fmt_int(x, _pos=None):
    """_summary_

    Args:
        x (_type_): _description_
        _pos (_type_, optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """
    if x >= 1_000_000:
        return f"{x/1_000_000:.1f}M"
    if x >= 1_000:
        return f"{x/1_000:.1f}k"
    return f"{int(x):d}"

def plot_daily_cases_last_30_days(
    db_path: str | Path,
    out_path: str | Path,
    table: str = "srag_data",
    date_col: str = "DT_SIN_PRI",
    where_clause: Optional[str] = None,
    json_path: str = None,
    rolling_days: int = 7,
    ) -> None:
    """_summary_

    Args:
        db_path (str | Path): _description_
        out_path (str | Path): _description_
        table (str, optional): _description_. Defaults to "srag_data".
        date_col (str, optional): _description_. Defaults to "DT_SIN_PRI".
        where_clause (Optional[str], optional): _description_. Defaults to None.
        rolling_days (int, optional): _description_. Defaults to 7.

    Raises:
        ValueError: _description_

    Returns:
        _type_: _description_
    """
    df = fetch_dates_df(db_path, table, date_col, where_clause)
    if df.empty:
        raise ValueError("Nenhum registro com data válida para o filtro informado.")

    last_date = df["dt"].max().normalize()
    first_plot_date = last_date - pd.Timedelta(days=29)

    s_daily = (
        df.set_index("dt")
          .sort_index()
          .loc[first_plot_date:last_date]
          .groupby(pd.Grouper(freq="D"))
          .size()
          .rename("casos")
    )
    s_daily = s_daily.reindex(pd.date_range(first_plot_date, last_date, freq="D"), fill_value=0)
    daily_df = s_daily.to_frame()

    plt.rcParams.update({
        "axes.edgecolor": "#9aa0a6",
        "axes.titleweight": "bold",
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
    })

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11, 4.2))

    bars = ax.bar(s_daily.index, s_daily.values, width=0.9,
                  color="#4f87ff", edgecolor="#2a56c6", linewidth=0.3, alpha=0.9)

    # média móvel
    if rolling_days and rolling_days > 1:
        s_ma = s_daily.rolling(rolling_days, min_periods=1).mean()
        ax.plot(s_ma.index, s_ma.values, linewidth=2.2, color="#101935", alpha=0.9, label=f"Média {rolling_days}d")

    subtitle = f"(filtro: {where_clause})" if where_clause else ""
    ax.set_title(f"Casos diários | últimos 30 dias até {last_date.date()}".strip())
    ax.set_xlabel("")
    ax.set_ylabel("Casos/dia")

    # Eixo X: datas legíveis
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%b"))
    ax.tick_params(axis="x", rotation=0)
    fig.autofmt_xdate(rotation=0)

    # grid leve e formatação de eixo Y
    ax.yaxis.grid(True, linewidth=0.6, alpha=0.25)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(FuncFormatter(fmt_int))

    # legenda se houver média
    if rolling_days and rolling_days > 1:
        ax.legend(frameon=False, fontsize=9, loc="upper left")

    plt.tight_layout()
    fig.savefig(out_path.with_suffix(".png"), dpi=200)
    fig.savefig(out_path.with_suffix(".svg"))
    plt.close(fig)
    
    save_chart_data(
        df=daily_df,
        sqlite_path=db_path,
        output_path=json_path,
        filters=where_clause
    )

    return None

def plot_monthly_cases_last_12_months(
    db_path: str | Path,
    out_path: str | Path,
    table: str = "srag_data",
    date_col: str = "DT_SIN_PRI",
    where_clause: Optional[str] = None,
    json_path: str = None
    ) -> None:
    df = fetch_dates_df(db_path, table, date_col, where_clause)
    if df.empty:
        raise ValueError("Nenhum registro com data válida para o filtro informado.")

    last_date = df["dt"].max().normalize()
    last_month = pd.Timestamp(year=last_date.year, month=last_date.month, day=1)
    first_month = (last_month - pd.DateOffset(months=11)).normalize()

    s_monthly = (
        df.set_index("dt")
          .sort_index()
          .groupby(pd.Grouper(freq="MS"))
          .size()
          .rename("casos")
    )
    idx = pd.date_range(first_month, last_month, freq="MS")
    s_monthly = s_monthly.reindex(idx, fill_value=0)
    monthly_df = s_monthly.to_frame()

    plt.rcParams.update({
        "axes.edgecolor": "#9aa0a6",
        "axes.titleweight": "bold",
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9,
    })

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10.6, 4.2))

    ax.bar(s_monthly.index, s_monthly.values, width=24, 
           color="#00a37a", edgecolor="#0b5c49", linewidth=0.3, alpha=0.9)

    ax.set_title(
        f"Casos mensais | últimos 12 meses até {last_month.strftime('%Y-%m')}".strip()
    )
    ax.set_xlabel("")
    ax.set_ylabel("Casos/mês")

    # eixo X com rótulos compactos
    ax.set_xticks(s_monthly.index)
    ax.set_xticklabels([ts.strftime("%b/%y") for ts in s_monthly.index], rotation=0)

    ax.yaxis.grid(True, linewidth=0.6, alpha=0.25)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(FuncFormatter(fmt_int))


    plt.tight_layout()
    fig.savefig(out_path.with_suffix(".png"), dpi=200)
    fig.savefig(out_path.with_suffix(".svg"))
    plt.close(fig)
    
    save_chart_data(
        df=s_monthly,
        sqlite_path=db_path,
        output_path=json_path,
        filters=where_clause
    )
    return None

def _plot_single_metric(df: pd.DataFrame, config: Dict[str, str], output_path: Path, plot_type: str):
    """_summary_

    Args:
        df (pd.DataFrame): _description_
        config (Dict[str, str]): _description_
        output_path (Path): _description_
        plot_type (str): _description_
    """
    if df.empty:
        print(f"[AVISO] Nenhum dado para plotar para o gráfico: {config['title']}")
        return

    df = df.sort_values(by=config['x_col'])
    
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(11, 6))

    if plot_type == 'line':
        ax.plot(
            df[config['x_col']],
            df[config['y_col']],
            marker='o',
            linestyle='-',
            color='#00529B',
            label='Valor Mensal'
        )
    elif plot_type == 'bar':
        ax.bar(
            df[config['x_col']],
            df[config['y_col']],
            color='#4f87ff',
            width=0.8,
            label='Valor Mensal'
        )
    
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f'{y:.1f}%'))
    ax.set_title(config['title'], fontsize=16, weight='bold', pad=20)
    ax.set_ylabel(config['ylabel'], fontsize=12)
    ax.set_xlabel('Mês/Ano', fontsize=12)
    
    ax.tick_params(axis='x', rotation=45)
    ax.grid(True, which='major', linestyle='--', linewidth='0.5', color='grey')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    fig.savefig(output_path.with_suffix('.svg'))
    plt.close(fig)
    
def plot_static_metrics(bundle: MetricsBundle, output_dir: str | Path, plot_type: str = 'line') -> None:
    """
    Gera e salva gráficos para cada métrica em um MetricsBundle.

    Args:
        bundle (MetricsBundle): O objeto contendo os dados das métricas.
        output_dir (str | Path): O diretório onde os gráficos (PNG) serão salvos.
        plot_type (str): O tipo de gráfico a ser gerado ('line' ou 'bar'). Padrão: 'line'.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Validação do tipo de plot
    if plot_type not in ['line', 'bar']:
        raise ValueError(f"Tipo de gráfico inválido: '{plot_type}'. Escolha entre 'line' ou 'bar'.")
        
    print(f"Gerando gráficos do tipo '{plot_type}' no diretório: {output_path.absolute()}")

    for metric_name, config in METRIC_CONFIG.items():
        metric_series: MetricSeries = getattr(bundle, metric_name)
        df = pd.DataFrame(metric_series.rows)
        plot_filename = output_path / f"{metric_name}_{plot_type}.png" # Adiciona o tipo ao nome do arquivo

        # Passa o 'plot_type' para a função auxiliar
        _plot_single_metric(df, config, plot_filename, plot_type)
        
    print("Gráficos gerados com sucesso!")
