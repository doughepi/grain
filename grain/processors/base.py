import json
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import uuid4

from r2r import R2RClient, generate_id_from_label

from grain.logging import Logger

T = TypeVar("T")


class DataItem(Generic[T]):
    def __init__(
        self,
        unique_characteristic: str,
        filename: Path,
        metadata: Dict[str, Any],
        source: str,
    ) -> None:
        self.document_id: str = str(generate_id_from_label(unique_characteristic))
        self.filename: Path = filename
        self.metadata: Dict[str, Any] = {
            "source": source,
            **metadata,
        }

    def __eq__(self, value: object) -> bool:
        return isinstance(value, DataItem) and value.document_id == self.document_id

    def __repr__(self) -> str:
        return f"DataItem(document_id={self.document_id}, filename={self.filename}, metadata={self.metadata})"


class DataProcessor(ABC, Generic[T]):
    def __init__(
        self, logger: Logger, r2r_client: R2RClient = None, source: str = "Unknown"
    ) -> None:
        self.logger = logger
        self.r2r_client: R2RClient = r2r_client or R2RClient(
            base_url="http://localhost:8000"
        )
        self.source: str = source
        self.data: List[DataItem[T]] = []

    def mark_for_ingest(
        self,
        unique_characteristic: str,
        filename: Path,
        metadata: Dict[str, Any],
    ) -> None:
        item = DataItem(unique_characteristic, filename, metadata, self.source)
        self.data.append(item)

    def write_for_ingest(
        self,
        unique_characteristic: str,
        filename: Path,
        data: bytes,
        metadata: Dict[str, Any],
    ) -> None:
        item = DataItem(unique_characteristic, filename, metadata, self.source)
        with filename.open("wb") as f:
            f.write(data)
        self.data.append(item)

    def handle_new_data_item(self, item: DataItem[T]) -> str:
        try:
            return self.r2r_client.ingest_files(
                file_paths=[str(item.filename)],
                metadatas=[item.metadata],
                document_ids=[item.document_id],
            )
        except Exception as e:
            self.logger.error(f"Error processing {item.filename}: {e}")

    def handle_updated_data_item(
        self, item: DataItem[T], wait_on_processing: bool = False
    ) -> None:
        if wait_on_processing:
            while True:
                documents = self.r2r_client.documents_overview(
                    document_ids=[item.document_id]
                ).get("results", [])
                if len(documents) == 1 and documents[0]["status"] == "success":
                    break
                time.sleep(1)

        try:
            return self.r2r_client.update_files(
                file_paths=[str(item.filename)],
                metadatas=[item.metadata],
                document_ids=[item.document_id],
            )
        except Exception as e:
            self.logger.error(f"Error processing {item.filename}: {e}")

    def item_show_func(self, item: DataItem) -> str:
        return f"{item.filename}" if item else ""

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        documents = self.r2r_client.documents_overview(document_ids=[document_id])
        documents = documents.get("results", [])
        return documents[0] if documents else None

    def ingest(self, cleanup=False) -> None:
        with self.logger.progress(
            iterable=self.data, label="Processing", item_show_func=self.item_show_func
        ) as progress:
            for item in progress:
                document = self.get_document(item.document_id)
                if document:
                    status = document.get("status")
                    if status == "success":
                        self.handle_updated_data_item(item)
                    elif status == "processing":
                        self.handle_updated_data_item(item, wait_on_processing=True)
                else:
                    self.handle_new_data_item(item)

        if cleanup:
            for item in self.data:
                try:
                    item.filename.unlink()
                except Exception as e:
                    self.logger.error(f"Error cleaning up {item.filename}: {e}")
            self.data = []

    def get_unique_filename(self, extension: str) -> Path:
        return Path(f"{uuid4()}.{extension}")
