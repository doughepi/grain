from pathlib import Path
from tempfile import TemporaryDirectory
from typing import IO, Generator

from imap_tools import AND, MailBox
from imap_tools.message import MailMessage

from grain.logging import Logger
from grain.processors.base import DataProcessor


class EmailProcessor(DataProcessor[str]):
    def __init__(
        self,
        email_address: str,
        app_password: str,
        imap_server: str,
        mailbox: str,
        logger: Logger,
        r2r_client=None,
    ) -> None:
        super().__init__(logger=logger, source="Email", r2r_client=r2r_client)
        self.email_address = email_address
        self.app_password = app_password
        self.imap_server = imap_server
        self.mailbox = mailbox

    def fetch_emails(self) -> Generator[MailMessage, None, None]:
        with MailBox(self.imap_server).login(
            self.email_address, self.app_password, initial_folder=self.mailbox
        ) as mailbox:
            for msg in mailbox.fetch(AND(all=True)):
                yield msg

    def process_emails(self) -> None:
        self.logger.info("Fetching emails...")
        emails = self.fetch_emails()

        with TemporaryDirectory() as tmpdirname:
            tmpdir = Path(tmpdirname)
            for msg in emails:
                self.logger.info(f"Processing email: {msg.uid} - {msg.subject}")

                filename = tmpdir / self.get_unique_filename("html")

                self.write_for_ingest(
                    msg.uid,
                    filename,
                    msg.html.encode("utf-8"),
                    {
                        "subject": msg.subject or "No Subject",
                        "from": msg.from_,
                        "to": ", ".join(msg.to),
                        "date": msg.date_str,
                        "uid": msg.uid,
                    },
                )

            self.ingest(cleanup=True)

            self.logger.info("Processing completed successfully.")
