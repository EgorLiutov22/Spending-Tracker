from .base import BaseExporter
import pandas as pd
from io import BytesIO


class XLSXExporter(BaseExporter):
    @property
    def media_type(self) -> str:
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    @property
    def extension(self) -> str:
        return "xlsx"

    def _write_to_stream(self, df: pd.DataFrame, stream: BytesIO) -> None:
        df.to_excel(stream, index=False, engine="openpyxl")
