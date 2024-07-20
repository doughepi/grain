import json
import logging
import os
from pathlib import Path
from typing import List

import click
from dotenv import load_dotenv
from r2r import R2R, R2RClient, R2RConfig

from grain.logging import CLILogger, Logger
from grain.processors.directory import DirectoryProcessor
from grain.processors.imap import EmailProcessor
from grain.processors.messages import MessageProcessor
from grain.processors.notes import NotesProcessor

logging.basicConfig(level=logging.INFO)


class GrainConfig:
    def __init__(
        self, r2r: R2RClient, logger: Logger, username: str = None, password: str = None
    ):
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
@click.option("--username", default="admin@example.com")
@click.password_option(
    "--password", default="change_me_immediately", confirmation_prompt=False
)
@click.pass_obj
def r2r(config: GrainConfig, username: str, password: str) -> None:
    """Login to R2R."""
    logger = config.logger
    logger.info("Logging in to R2R.")
    r2r_client = config.r2r_client
    result = r2r_client.login(username, password)
    logger.info(result)


@r2r.command()
@click.option("--query", prompt="Query")
@click.option("--use_vector_search", default=True, type=bool)
@click.option("--search_filters", default={}, type=dict)
@click.option("--search_limit", default=10, type=int)
@click.option("--use_kg_search", default=False, type=bool)
@click.pass_obj
def rag(
    config: GrainConfig,
    query: str,
    use_vector_search: bool,
    search_filters: dict,
    search_limit: int,
    use_kg_search: bool,
) -> None:
    """Search R2R for data."""
    r2r_client = config.r2r_client
    result = r2r_client.rag(
        query,
        use_vector_search=use_vector_search,
        search_filters=search_filters,
        search_limit=search_limit,
        use_kg_search=use_kg_search,
    )
    content = result["results"]["completion"]["choices"][0]["message"]["content"]
    click.echo(content)


@r2r.command()
@click.pass_obj
def documents_overview(config: GrainConfig) -> None:
    """Get an overview of the documents in R2R."""
    r2r_client = config.r2r_client
    result = r2r_client.documents_overview()
    click.echo(json.dumps(result, indent=2))


@cli.group()
@click.option("--username", default="admin@example.com")
@click.password_option("--password", default="change_me_immediately")
@click.pass_obj
def process(config: GrainConfig, username: str, password: str) -> None:
    """Process and upload data to R2R."""
    logger = config.logger
    logger.info("Logging in to R2R.")
    r2r_client = config.r2r_client
    result = r2r_client.login(username, password)
    logger.info(result)


@process.command()
@click.option(
    "--db-path",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to the messages database.",
)
@click.pass_obj
def messages(config: GrainConfig, db_path: Path) -> None:
    """Fetch, process, and upload messages to R2R."""
    message_processor = MessageProcessor(
        logger=config.logger, db_path=db_path, r2r_client=config.r2r_client
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


@cli.command()
@click.option("--config-path", type=click.Path(exists=True, path_type=Path))
@click.option("--host", default="localhost")
@click.option("--port", default=8000)
def serve(config_path: Path, host: str, port: int) -> None:
    """Serve data from R2R."""
    load_dotenv()
    config = R2RConfig.from_json(config_path)
    r2r = R2R(config=config)
    r2r.serve(host=host, port=port)


if __name__ == "__main__":
    cli()
