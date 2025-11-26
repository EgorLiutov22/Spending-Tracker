from .base import BaseExporter
import pandas as pd
from io import BytesIO


class CSVExporter(BaseExporter):
    @property
    def media_type(self) -> str:
        return "text/csv"

    @property
    def extension(self) -> str:
        return "csv"

    def _write_to_stream(self, df: pd.DataFrame, stream: BytesIO) -> None:
        df.to_csv(stream, index=False)
