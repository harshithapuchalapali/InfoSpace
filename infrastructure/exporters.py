import csv
import json
import logging
import os
from typing import Any, Optional

from domain import DataExporterPort

logger = logging.getLogger(__name__)


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


class CsvExporter(DataExporterPort):
    def export(self, data: list[dict], filepath: str) -> str:
        if not data:
            logger.warning("No data to export - skipping CSV.")
            return ""
        _ensure_dir(os.path.dirname(filepath) or ".")
        fieldnames = list(data[0].keys())
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        abs_path = os.path.abspath(filepath)
        logger.info("Exported CSV -> %s", abs_path)
        return abs_path


class JsonExporter(DataExporterPort):
    def __init__(self, indent: int = 2, ensure_ascii: bool = False):
        self.indent = indent
        self.ensure_ascii = ensure_ascii

    def export(self, data: Any, filepath: str) -> str:
        _ensure_dir(os.path.dirname(filepath) or ".")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=self.indent, ensure_ascii=self.ensure_ascii)
        abs_path = os.path.abspath(filepath)
        logger.info("Exported JSON -> %s", abs_path)
        return abs_path
