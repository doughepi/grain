from abc import ABC, abstractmethod
import time
from typing import Any, Generator, List, Dict, Tuple, TypeVar, Generic
import click
from r2r import R2RClient, generate_id_from_label
from imessage_reader.fetch_data import FetchData
from tempfile import TemporaryDirectory
import json
from enum import Enum
import logging
from macnotesapp import Note, NotesApp
from imap_tools import MailBox, AND
from imap_tools.message import MailMessage, MailAttachment
import os
from uuid import uuid4

logging.basicConfig(level=logging.INFO)

client = R2RClient(base_url="http://localhost:8000")

MESSAGES_DB_PATH = "/Users/doughepi/Library/Messages/chat.db"

T = TypeVar("T")


class Source(Enum):
    MESSAGES = "Messages"
    NOTES = "Notes"
    EMAIL = "Email"


BATCH_SIZE = 1


class DataItem(Generic[T]):
    def __init__(
        self,
        unique_characteristic: str,
        filename: str,
        data: T,
        metadata: Dict[str, Any],
        source: Source,
    ) -> None:
        self.document_id: str = str(generate_id_from_label(unique_characteristic))
        self.filename: str = filename
        self.data: T = data
        self.metadata: Dict[str, Any] = {
            "source": source.value,
            **metadata,
        }

    def __repr__(self) -> str:
        return f"DataItem(document_id={self.document_id}, filename={self.filename}, metadata={self.metadata})"


class DataProcessor(ABC, Generic[T]):
    def __init__(self, source: Source) -> None:
        self.source: Source = source
        self.data: List[DataItem[T]] = []

    def add_data(
        self,
        unique_characteristic: str,
        filename: str,
        data: T,
        metadata: Dict[str, Any],
    ) -> None:
        item = DataItem(unique_characteristic, filename, data, metadata, self.source)
        self.data.append(item)

    def write_data_to_files(self) -> None:
        for item in self.data:
            with open(item.filename, "w") as f:
                self.write_file(f, item.data)

    @abstractmethod
    def write_file(self, fp: Any, data: T) -> None:
        """Override this method in subclasses to handle different file formats."""
        pass

    def get_existing_document_ids(self) -> set:
        existing_documents = client.documents_overview()
        return {doc["document_id"] for doc in existing_documents["results"]}

    def process_existing_files(self, client_method: Any) -> None:
        existing_document_ids = self.get_existing_document_ids()
        to_update = [
            item for item in self.data if item.document_id in existing_document_ids
        ]
        if to_update:
            click.echo("Updating existing files...")
            self.batch_process(client_method, to_update)
            click.echo("Update successful.")

    def process_new_files(self, client_method: Any) -> None:
        existing_document_ids = self.get_existing_document_ids()
        to_ingest = [
            item for item in self.data if item.document_id not in existing_document_ids
        ]
        if to_ingest:
            click.echo("Ingesting new files...")
            self.batch_process(client_method, to_ingest)
            click.echo("Ingest successful.")

    def flush(self) -> None:
        for item in self.data:
            os.remove(item.filename)
        self.data.clear()

    def save(self) -> None:
        self.write_data_to_files()
        self.process_existing_files(client.update_files)
        self.process_new_files(client.ingest_files)
        self.flush()

    def batch_process(self, client_method: Any, items: List[DataItem[T]]) -> None:
        for i in range(0, len(items), BATCH_SIZE):
            batch = items[i : i + BATCH_SIZE]
            try:
                client_method(
                    file_paths=[item.filename for item in batch],
                    metadatas=[item.metadata for item in batch],
                    document_ids=[item.document_id for item in batch],
                )
            except Exception as e:
                click.echo(f"Error processing batch: {e}")
            time.sleep(0.2)

    def get_unique_filename(self, extension: str) -> str:
        return f"{uuid4()}.{extension}"


class ChatProcessor(DataProcessor[List[Tuple[str, str, str, str]]]):
    def __init__(self) -> None:
        super().__init__(Source.MESSAGES)

    def fetch_chats(self) -> List[Tuple[str, str, str, str]]:
        fetch_data = FetchData(db_path=MESSAGES_DB_PATH)
        return fetch_data.get_messages()

    def process_chats(self) -> None:
        data = self.fetch_chats()

        with TemporaryDirectory() as tmpdirname:
            click.echo("Fetching chats...")

            users = {}
            for row in data:

                # Combine all messages to the same user.
                if row[0] in users:
                    users[row[0]].append(row)
                else:
                    users[row[0]] = [row]

            for user, messages in users.items():
                click.echo(f"Processing chat with {user}...")

                filename = f"{tmpdirname}/{self.get_unique_filename('json')}"

                self.add_data(
                    user,
                    filename,
                    messages,
                    {
                        "user": user,
                    },
                )

            self.save()

            click.echo("Processing completed successfully.")

    def write_file(self, f: Any, data: List[Tuple[str, str, str, str]]) -> None:
        f.write(json.dumps(data))


class NotesProcessor(DataProcessor[str]):
    def __init__(self) -> None:
        super().__init__(Source.NOTES)

    def fetch_notes(self) -> List[Note]:
        notesapp = NotesApp()
        return notesapp.notes()

    def process_notes(self) -> None:
        data = self.fetch_notes()

        with TemporaryDirectory() as tmpdirname:
            click.echo("Writing notes to temporary files...")

            for note in data:
                if note.password_protected:
                    continue

                self.add_data(
                    note.id,
                    f"{tmpdirname}/{self.get_unique_filename('html')}",
                    note.body,
                    {
                        "account": note.account,
                        "folder": note.folder,
                        "name": note.name,
                        "id": note.id,
                    },
                )

            self.save()

            click.echo("Processing completed successfully.")

    def write_file(self, f: Any, data: str) -> None:
        f.write(data)


class EmailProcessor(DataProcessor[str]):
    def __init__(
        self, email_address: str, app_password: str, imap_server: str, mailbox: str
    ) -> None:
        super().__init__(Source.EMAIL)
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
        click.echo("Fetching emails...")
        emails = self.fetch_emails()

        with TemporaryDirectory() as tmpdirname:
            for msg in emails:
                click.echo(f"Processing email: {msg.uid} - {msg.subject}")

                filename = f"{tmpdirname}/{self.get_unique_filename('html')}"

                self.add_data(
                    msg.uid,
                    filename,
                    msg.html,
                    {
                        "subject": msg.subject or "No Subject",
                        "from": msg.from_,
                        "to": ", ".join(msg.to),
                        "date": msg.date_str,
                        "uid": msg.uid,
                    },
                )

            self.save()

            click.echo("Processing completed successfully.")

    def write_file(self, f: Any, data: str) -> None:
        f.write(data)


@click.group()
def cli() -> None:
    """A CLI tool for processing iMessages and updating the R2RClient."""
    pass


@click.command()
def process_chats() -> None:
    """Fetch, process, and upload chats to the R2RClient."""
    chat_processor = ChatProcessor()
    chat_processor.process_chats()


@click.command()
def process_notes() -> None:
    """Fetch, process, and upload notes to the R2RClient."""
    notes_processor = NotesProcessor()
    notes_processor.process_notes()


@click.command()
@click.option("--email", prompt="Email Address")
@click.option("--password", prompt="App Password")
@click.option("--imap_server", default="imap.mail.me.com")
@click.option("--mailbox", default="inbox")
def process_emails(email: str, password: str, imap_server: str, mailbox: str) -> None:
    """Fetch, process, and upload emails to the R2RClient."""
    email_processor = EmailProcessor(email, password, imap_server, mailbox)
    email_processor.process_emails()


cli.add_command(process_chats)
cli.add_command(process_notes)
cli.add_command(process_emails)

if __name__ == "__main__":
    cli()
