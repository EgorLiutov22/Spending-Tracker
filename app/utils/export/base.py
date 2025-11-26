from abc import ABC, abstractmethod
from io import BytesIO
from typing import List, Dict
import pandas as pd
from fastapi.responses import StreamingResponse


class BaseExporter(ABC):
    """Базовый класс для всех экспортёров с общей логикой"""

    def export(self, data: List[Dict]) -> StreamingResponse:
        if not data:
            raise ValueError("No data to export")

        df = pd.DataFrame(data)
        stream = BytesIO()

        self._write_to_stream(df, stream)

        stream.seek(0)
        return StreamingResponse(
            stream,
            media_type=self.media_type,
            headers={"Content-Disposition": f"attachment; filename=report.{self.extension}"}
        )

    @property
    @abstractmethod
    def media_type(self) -> str:
        """MIME-тип ответа (например, 'text/csv')"""
        pass

    @property
    @abstractmethod
    def extension(self) -> str:
        """Расширение файла (например, 'csv')"""
        pass

    @abstractmethod
    def _write_to_stream(self, df: pd.DataFrame, stream: BytesIO) -> None:
        """Специфичная логика записи в поток"""
        pass
