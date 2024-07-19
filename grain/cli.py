import logging
import os
from pathlib import Path
from typing import List

import click
from r2r import R2RClient

from grain.logging import CLILogger, Logger
from grain.processors.directory import DirectoryProcessor
from grain.processors.imap import EmailProcessor
from grain.processors.messages import MessageProcessor
from grain.processors.notes import NotesProcessor

logging.basicConfig(level=logging.INFO)


class GrainConfig:
    def __init__(self, r2r: R2RClient, logger: Logger) -> None:
        self.r2r_client = r2r
        self.logger = logger


@click.group()
@click.option("--telemetry/--no-telemetry", default=True)
@click.pass_context
def cli(context, telemetry: bool) -> None:
    """A CLI tool for processing various forms of data for ingestion into R2R."""
    if not telemetry:
        logging.info("Disabling telemetry.")
        os.environ["TELEMETRY_ENABLED"] = "false"

    client = R2RClient(base_url="http://localhost:8000")
    context.obj = GrainConfig(client, logger=CLILogger())


@cli.group()
def process() -> None:
    """Process and upload data to R2R."""
    pass


@process.command()
@click.pass_obj
def messages(config: GrainConfig) -> None:
    """Fetch, process, and upload messages to R2R."""
    message_processor = MessageProcessor(
        r2r_client=config.r2r_client, logger=config.logger
    )
    message_processor.process_messages()


@process.command()
@click.pass_obj
def notes(config: GrainConfig) -> None:
    """Fetch, process, and upload notes to R2R."""
    notes_processor = NotesProcessor(r2r_client=config.r2r_client, logger=config.logger)
    notes_processor.process_notes()


@process.command()
@click.option("--email", prompt="Email Address")
@click.password_option("--password", prompt="App Password")
@click.option("--imap_server", default="imap.mail.me.com")
@click.option("--mailbox", default="inbox")
@click.pass_obj
def imap(
    config: GrainConfig, email: str, password: str, imap_server: str, mailbox: str
) -> None:
    """Fetch, process, and upload emails to R2R."""
    email_processor = EmailProcessor(
        email,
        password,
        imap_server,
        mailbox,
        logger=config.logger,
        r2r_client=config.r2r_client,
    )
    email_processor.process_emails()


@process.command()
@click.argument("directory", type=click.Path(exists=True, path_type=Path))
@click.option("--recursive/--no-recursive", default=False)
@click.option("--extensions", multiple=True)
@click.pass_obj
def directory(
    config: GrainConfig, directory: Path, recursive: bool, extensions: List[str]
) -> None:
    """Process and upload files in a directory to R2R."""
    directory_processor = DirectoryProcessor(
        logger=config.logger, r2r_client=config.r2r_client
    )
    directory_processor.process_directory(
        path=directory, recursive=recursive, extensions=extensions
    )


if __name__ == "__main__":
    cli()
