import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import IO, Generator, List

from grain.logging import Logger
from grain.processors.base import DataProcessor


class DirectoryProcessor(DataProcessor[bytes]):
    def __init__(self, logger: Logger, r2r_client=None) -> None:
        super().__init__(logger=logger, source="Directory", r2r_client=r2r_client)

    def fetch_directory(
        self, path: Path, recursive: bool = True, extensions: List[str] = ["txt", "md"]
    ) -> Generator[Path, None, None]:
        """Get all the files in the directory filtered by the file extension."""
        files = []
        func = path.rglob if recursive else path.glob
        for file in func("*"):

            # Suffix has a leading dot. We don't want that.
            if file.is_file() and file.suffix[1:] in extensions:
                files.append(file)

        return files

    def compute_file_hash(self, file_path: Path, hash_type: str = "sha256") -> str:
        """Compute the hash of the file's contents."""
        hash_func = hashlib.new(hash_type)
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()

    def process_directory(
        self,
        path: Path,
        recursive: bool = False,
        extensions: List[str] = ["txt", "md"],
    ) -> None:
        files = self.fetch_directory(
            path=path, recursive=recursive, extensions=extensions
        )

        for file_path in files:
            self.logger.info(f"Processing file: {file_path}")

            file_hash = self.compute_file_hash(file_path)

            self.mark_for_ingest(
                file_hash,  # Using the file hash as the unique identifier
                file_path,
                {
                    "path": str(file_path),
                    "name": file_path.name,
                    "suffix": file_path.suffix,
                    "hash": file_hash,
                    "stem": file_path.stem,
                },
            )

            # Save each file so that we're not storing everything in memory.
            self.ingest(
                cleanup=False
            )  # Cleanup is False to keep the files because we're reading from a place we don't control.

        self.logger.info("Processing completed successfully.")
