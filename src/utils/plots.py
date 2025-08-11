import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter

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
    rolling_days: int = 7,
) -> None:
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

    return daily_df

def plot_monthly_cases_last_12_months(
    db_path: str | Path,
    out_path: str | Path,
    table: str = "srag_data",
    date_col: str = "DT_SIN_PRI",
    where_clause: Optional[str] = None,
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
    return None
