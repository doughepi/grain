import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import IO, Any, Callable, Dict, Generic, List, Optional, TypeVar
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
        with filename.open(filename, "wb") as f:
            f.write(data)
        self.data.append(item)

    def get_existing_document_ids(self) -> set:
        existing_documents = self.r2r_client.documents_overview()
        return {doc["document_id"] for doc in existing_documents["results"]}

    def process_existing_files(self, client_method: Any) -> None:
        existing_document_ids = self.get_existing_document_ids()
        to_update = [
            item for item in self.data if item.document_id in existing_document_ids
        ]
        if to_update:
            self.logger.info("Updating existing files...")
            self.batch_process(client_method, to_update)
            self.logger.info("Update successful.")

    def process_new_files(self, client_method: Any) -> None:
        existing_document_ids = self.get_existing_document_ids()
        to_ingest = [
            item for item in self.data if item.document_id not in existing_document_ids
        ]
        if to_ingest:
            self.logger.info("Ingesting new files...")
            self.batch_process(client_method, to_ingest)
            self.logger.info("Ingest successful.")

    def ingest(self, cleanup=False) -> None:
        self.process_existing_files(self.r2r_client.update_files)
        self.process_new_files(self.r2r_client.ingest_files)

        if cleanup:
            for item in self.data:
                item.filename.unlink()
            self.data = []

    def batch_process(
        self, client_method: Any, items: List[DataItem[T]], batch_size: int = 5
    ) -> None:

        def item_show_function(batch: Optional[List[DataItem]]) -> Optional[str]:
            # Concatenate the document IDs for the progress bar.
            if batch:
                return ", ".join(item.filename.name for item in batch)

        with self.logger.progress(
            "Uploading to R2R...",
            length=len(items),
            show_percent=True,
            color=True,
            item_show_func=item_show_function,
        ) as progress:
            for i in range(0, len(items), batch_size):
                batch = items[i : i + batch_size]
                try:
                    client_method(
                        file_paths=[str(item.filename) for item in batch],
                        metadatas=[item.metadata for item in batch],
                        document_ids=[item.document_id for item in batch],
                    )
                    progress.update(len(batch), batch)
                except Exception as e:
                    self.logger.error(
                        f"Error processing batch: {e}", extra={"batch_size": len(batch)}
                    )
                time.sleep(0.2)

    def get_unique_filename(self, extension: str) -> Path:
        return Path(f"{uuid4()}.{extension}")
