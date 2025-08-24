import json
import os
import tempfile
from pathlib import Path
import pandas as pd
from datetime import datetime, timezone, date
from typing import Any, Dict, Optional
import markdown
#from weasyprint import HTML, CSS


def _json_default(o: Any):
    """Serializes datetime and date objects into ISO format for JSON.

    This function is intended to be used as the `default` parameter in `json.dump()` or `json.dumps()`.
    It handles objects that are not natively JSON serializable by converting `datetime` and `date`
    objects to a standard string representation.

    Args:
        o (Any): The object to be serialized.

    Raises:
        TypeError: If the object is not a `datetime` or `date` instance and is not otherwise JSON serializable.

    Returns:
        str: The ISO 8601 formatted string representation of the object.
    """
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    raise TypeError(f"Object of type {type(o)} is not JSON serializable")


def save_json_atomic(payload: Dict[str, Any], output_path: str) -> Optional[Path]:
    """Atomically saves a dictionary to a JSON file.

    This function writes the JSON data to a temporary file first, and then
    atomically replaces the final output file. This prevents file corruption
    if the process is interrupted during the write operation.

    Args:
        payload (Dict[str, Any]): The dictionary containing the data to be saved.
        output_path (str): The final destination path for the JSON file.

    Returns:
        Optional[Path]: A Path object for the saved file on success, or None on failure.
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
    description: str = None,
) -> Optional[Path]:
    """Prepares and saves chart data from a DataFrame to a JSON file.

    This function structures a pandas DataFrame into a dictionary payload containing
    metadata and a list of data points. It then uses the `save_json_atomic`
    function to safely write this data to a JSON file.

    Args:
        df (pd.DataFrame): The input DataFrame with a datetime index and a single column of numerical data.
        sqlite_path (Union[str, Path]): The path to the SQLite database file from which the data was queried.
        output_path (Union[str, Path]): The path where the final JSON file will be saved.
        filters (Optional[str], optional): A string detailing any filters applied to the data. Defaults to None.
        description (Optional[str], optional): A descriptive summary of the data being saved. Defaults to None.

    Returns:
        Optional[Path]: A Path object for the saved file on success, or None on failure.
    """
    payload = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sqlite_path": str(sqlite_path),
            "date_range": {
                "start": df.index.min().strftime("%Y-%m-%d"),
                "end": df.index.max().strftime("%Y-%m-%d"),
            },
            "filters": filters or None,
            "description": description,
        },
        "data": [
            {"date": d.strftime("%Y-%m-%d"), "cases": int(v)}
            for d, v in zip(df.index, df.values)
        ],
    }
    save_json_atomic(payload=payload, output_path=output_path)


def load_json(json_path: str) -> Dict[str, str]:
    """Loads data from a JSON file into a Python dictionary.

    Args:
        json_path (str): The file path to the JSON file to be loaded.

    Returns:
        Dict[str, str]: The data from the JSON file as a dictionary.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def extrair_ia_summary(json_path: str) -> Dict[str, str]:
    """Loads a JSON file and extracts AI-generated summaries for each metric.

    This function reads a JSON file, typically containing metric data, and filters it to create a dictionary of
    just the 'ia_summary' fields. This is useful for isolating the AI-generated text for further use in a report.

    Args:
        json_path (str): The file path to the JSON file to be processed.

    Returns:
        Dict[str, str]: A dictionary where keys are metric names and values are their corresponding AI summaries.
    """
    data = load_json(json_path=json_path)

    summaries = {
        nome_metrica: conteudo.get("ia_summary", "")
        for nome_metrica, conteudo in data.get("metrics", {}).items()
        if "ia_summary" in conteudo
    }

    return summaries

def markdown_to_pdf(md_path: str, pdf_path: str) -> None:
    """
    Function to convert markdown file into PDF.

    Args:
        md_path (str): The file path to the markdown file to be processed.
        pdf_parh (str): The file path where the pdf will be saved.

    Returns: None
    """

    md_text = Path(md_path).read_text(encoding="utf-8")
    
    # Convert to HTML
    html_text = markdown.markdown(md_text, extensions=["fenced_code", "tables"])
    
    # Optional: Add CSS to preserve Markdown styles
    css = CSS(string="""
        body { font-family: "Arial", sans-serif; margin: 40px; }
        h1, h2, h3 { font-weight: bold; margin-top: 20px; }
        code { background: #f4f4f4; padding: 2px 4px; border-radius: 4px; }
        pre { background: #f4f4f4; padding: 10px; border-radius: 6px; overflow-x: auto; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; }
        th { background: #f9f9f9; }
    """)

    # Convert HTML to PDF
    HTML(string=html_text).write_pdf(pdf_path, stylesheets=[css])
