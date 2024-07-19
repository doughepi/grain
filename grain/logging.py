import logging
from abc import ABC, abstractmethod

import click


class Logger(ABC):
    @abstractmethod
    def info(self, message: str) -> None:
        pass

    @abstractmethod
    def error(self, message: str) -> None:
        pass

    @abstractmethod
    def progress(self, label: str, length: int) -> "Progress":
        pass


class Progress(ABC):
    @abstractmethod
    def update(self, n: int) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass


class StandardLogger(Logger):
    def __init__(self) -> None:
        logging.basicConfig(level=logging.INFO)

    def info(self, message: str) -> None:
        logging.info(message)

    def error(self, message: str) -> None:
        logging.error(message)

    def progress(self, label: str, length: int) -> Progress:
        return StandardProgress(label, length)


class StandardProgress(Progress):
    def __init__(self, label: str, length: int) -> None:
        self.label = label
        self.length = length

    def update(self, n: int) -> None:
        pass  # Implement logging-based progress if needed

    def close(self) -> None:
        pass  # Implement closing logic if needed


class CLILogger(Logger):
    def info(self, message: str) -> None:
        click.echo(click.style(message, fg="green"))

    def error(self, message: str) -> None:
        click.echo(click.style(message, fg="red"), err=True)

    def progress(self, label: str, length: int) -> Progress:
        return click.progressbar(length=length, label=label)
