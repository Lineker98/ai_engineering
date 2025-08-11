import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
from typing import Optional

def save_chart_data(
    df: pd.DataFrame,
    sqlite_path: str | Path,
    output_path: str | Path,
    filters: Optional[str] = None
    ) -> Optional[Path]:
    """_summary_

    Args:
        df (pd.DataFrame): _description_
        sqlite_path (str | Path): _description_
        output_path (str | Path): _description_
        filters (Optional[str], optional): _description_. Defaults to None.

    Returns:
        Optional[Path]: _description_
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # monta payload
    payload = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sqlite_path": str(sqlite_path),
            "date_range": {
                "start": df.index.min().strftime("%Y-%m-%d"),
                "end": df.index.max().strftime("%Y-%m-%d")
            },
            "filters": filters or None
        },
        "data": [
            {"date": d.strftime("%Y-%m-%d"), "cases": int(v)}
            for d, v in zip(df.index, df.values)
        ]
    }

    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=str(path.parent), delete=False) as tmp:
            json.dump(payload, tmp, ensure_ascii=False, indent=2)
            tmp_name = tmp.name

        os.replace(tmp_name, path)
        return path
    except Exception as e:
        print(f"[ERRO] Falha ao salvar dados do gráfico: {e}")
        return None
    finally:
        if tmp_name and Path(tmp_name).exists():
            try:
                os.remove(tmp_name)
            except OSError:
                pass
