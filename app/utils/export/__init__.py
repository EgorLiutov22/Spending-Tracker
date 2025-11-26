from typing import Dict
from .base import BaseExporter
from .csv_exporter import CSVExporter
from .xlsx_exporter import XLSXExporter

EXPORTERS: Dict[str, BaseExporter] = {
    "csv": CSVExporter(),
    "xlsx": XLSXExporter(),
}


def get_exporter(format: str) -> BaseExporter:
    """Фабрика: возвращает нужный экспортер по имени формата"""
    if format not in EXPORTERS:
        raise ValueError(f"Unsupported export format: {format}. Supported: {list(EXPORTERS.keys())}")
    return EXPORTERS[format]
