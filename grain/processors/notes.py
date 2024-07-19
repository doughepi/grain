from pathlib import Path
from tempfile import TemporaryDirectory
from typing import IO, List

from macnotesapp import Note, NotesApp

from grain.logging import Logger
from grain.processors.base import DataProcessor


class NotesProcessor(DataProcessor[str]):
    def __init__(self, logger: Logger, r2r_client=None) -> None:
        super().__init__(logger=logger, source="Notes", r2r_client=r2r_client)

    def fetch_notes(self) -> List[Note]:
        notesapp = NotesApp()
        return notesapp.notes()

    def process_notes(self) -> None:
        data = self.fetch_notes()

        with TemporaryDirectory() as tmpdirname:
            self.logger.info("Writing notes to temporary files...")

            tmpdir = Path(tmpdirname)
            for note in data:
                if note.password_protected:
                    continue

                filename = tmpdir / self.get_unique_filename("html")

                self.write_for_ingest(
                    note.id,
                    filename,
                    note.body.encode("utf-8"),
                    {
                        "account": note.account,
                        "folder": note.folder,
                        "name": note.name,
                        "id": note.id,
                    },
                )

            self.ingest(cleanup=True)

            self.logger.info("Processing completed successfully.")
