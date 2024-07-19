import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import IO, List, Tuple

from imessage_reader.fetch_data import FetchData

from grain.logging import Logger
from grain.processors.base import DataProcessor

MESSAGES_DB_PATH = Path("/Users/doughepi/Library/Messages/message.db")


class MessageProcessor(DataProcessor[List[Tuple[str, str, str, str]]]):
    def __init__(self, logger: Logger, r2r_client=None) -> None:
        super().__init__(logger=logger, source="Messages", r2r_client=r2r_client)

    def fetch_messages(self) -> List[Tuple[str, str, str, str]]:
        fetch_data = FetchData(db_path=MESSAGES_DB_PATH)
        return fetch_data.get_messages()

    def process_messages(self) -> None:
        data = self.fetch_messages()

        with TemporaryDirectory() as tmpdirname:
            self.logger.info("Fetching messages...")

            tmpdir = Path(tmpdirname)
            users = {}
            for row in data:
                # Combine all messages to the same user.
                if row[0] in users:
                    users[row[0]].append(row)
                else:
                    users[row[0]] = [row]

            with self.logger.progress(
                label="Processing messages", length=len(users)
            ) as progress:
                for user, messages in users.items():
                    self.logger.info(f"Processing message with {user}...")

                    filename = tmpdir / self.get_unique_filename("json")

                    self.write_for_ingest(
                        user,
                        filename,
                        json.dumps(messages).encode("utf-8"),
                        {
                            "user": user,
                        },
                    )

                    self.ingest(cleanup=True)
                    progress.update(1)

            self.logger.info("Processing completed successfully.")