from typing import Dict
from enum import Enum
from .base import BaseExporter
from .csv_exporter import CSVExporter
from .xlsx_exporter import XLSXExporter


class ExportFormat(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"


EXPORTERS: Dict[str, BaseExporter] = {
    ExportFormat.CSV.value: CSVExporter(),
    ExportFormat.XLSX.value: XLSXExporter(),
}


def get_exporter(format_value: str) -> BaseExporter:
    if format_value not in EXPORTERS:
        raise ValueError(f"Unsupported format: {format_value}")
    return EXPORTERS[format_value]
