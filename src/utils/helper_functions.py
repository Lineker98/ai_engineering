import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
from typing import Optional, Dict

from pathlib import Path
from datetime import datetime, timezone, date
import tempfile, json, os
from typing import Any, Dict, Optional


def _json_default(o: Any):
    """_summary_

    Args:
        o (Any): _description_

    Raises:
        TypeError: _description_

    Returns:
        _type_: _description_
    """
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    raise TypeError(f"Object of type {type(o)} is not JSON serializable")


def save_json_atomic(payload: Dict[str, Any], output_path: str) -> Optional[Path]:
    """_summary_

    Args:
        payload (Dict[str, Any]): _description_
        output_path (str): _description_

    Returns:
        Optional[Path]: _description_
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=str(path.parent), delete=False
        ) as tmp:
            json.dump(payload, tmp, ensure_ascii=False, indent=2, default=_json_default)
            tmp_name = tmp.name

        os.replace(tmp_name, path)  # atomic on same filesystem
        return path
    except Exception as e:
        print(f"[ERRO] Falha ao salvar JSON: {e}")
        return None
    finally:
        if tmp_name and Path(tmp_name).exists():
            try:
                os.remove(tmp_name)
            except OSError:
                pass


def save_chart_data(
    df: pd.DataFrame,
    sqlite_path: str | Path,
    output_path: str | Path,
    filters: Optional[str] = None,
    description: str = None
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
    payload = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sqlite_path": str(sqlite_path),
            "date_range": {
                "start": df.index.min().strftime("%Y-%m-%d"),
                "end": df.index.max().strftime("%Y-%m-%d")
            },
            "filters": filters or None,
            "description": description
        },
        "data": [
            {"date": d.strftime("%Y-%m-%d"), "cases": int(v)}
            for d, v in zip(df.index, df.values)
        ]
    }
    save_json_atomic(payload=payload, output_path=output_path)
