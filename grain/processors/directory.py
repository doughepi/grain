import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import IO, Generator, List

from r2r import generate_id_from_label

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

            # I guess if a file is empty or only contains whitespace or line feeds, we can skip it.
            with open(file_path, "r") as f:
                if not f.read().strip():
                    self.logger.info(f"Skipping empty file: {file_path}")
                    continue

            id = str(generate_id_from_label(str(file_path)))

            self.mark_for_ingest(
                id,  # Using the file hash as the unique identifier
                file_path,
                {
                    "path": str(file_path),
                    "name": file_path.name,
                    "suffix": file_path.suffix,
                    "stem": file_path.stem,
                },
            )

        self.ingest(
            cleanup=False
        )  # Cleanup is False to keep the files because we're reading from a place we don't control.

        self.logger.info("Processing completed successfully.")
