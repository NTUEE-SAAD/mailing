##########################################################################
# File:         send_mail.py                                             #
# Purpose:      Automatically send batch of mails                        #
# Last changed: 2022/07/16                                               #
# Author:       zhuang-jia-xu                                            #
# Edited:                                                                #
# Copyleft:     (ɔ)NTUEE                                                 #
##########################################################################
import typer
from rich import print

import os
import logging
import shutil
from pathlib import Path
from typing import Optional

from .utils import *
from .AutoMailer import AutoMailer
from .Letter import Letter


app = typer.Typer()


@app.command()
def send(
    letter_path: Optional[str] = typer.Argument(None, help="Path to letter"),
    test: bool = typer.Option(
        False, "--test", "-t", help="Test mode: send mail to yourself"
    ),
    config_path: str = typer.Option(
        "config.ini",
        "--config",
        "-c",
        help="Path to config.ini",
        exists=True,
        dir_okay=False,
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Quiet mode: less output"),
    debugLevel: int = typer.Option(
        logging.NOTSET, "--debug", "-d", help="Debug level", min=0, max=5, clamp=True,
    ),
):
    """send emails to a list of recipients as configured in your letter"""

    if letter_path is None:
        letter_names = list(
            filter(lambda letter: Path(letter).is_dir(), os.listdir("."),)
        )

        if len(letter_names) == 0:
            richError(
                f"Can't find any letters in {os.getcwd()}, please specify a letter path"
            )

        letter_name = typerSelect("Please select a letter", letter_names)
        letter_path = Path("letters") / letter_name

    print(f"Using letter [blue]{letter_path}\n")

    if not Letter.check_letter(letter_path):
        richError(f"Invalid letter: {letter_path}")
        return

    # create log file if it doesn't exist
    if not (Path(letter_path) / "log.txt").exists():
        with open(Path(letter_path) / "log.txt", "w") as f:
            pass

    setup_logger(Path(letter_path) / "log.txt", debugLevel)

    auto_mailer_config = AutoMailer.load_mailer_config(config_path)
    auto_mailer = AutoMailer(auto_mailer_config, quiet=quiet)
    emails = Letter(
        letter_path,
        auto_mailer_config["account"]["name"],
        complete_school_email(auto_mailer_config["account"]["userid"]),
    )
    auto_mailer.connect()
    auto_mailer.send_emails(emails, test=test)
    auto_mailer.check_bounce_backs()


@app.command()
def create(letter_name: Optional[str] = typer.Argument(..., help="Name of letter")):
    """create a new letter from template"""
    typer.echo("Creating a new letter")

    TEMPLATE_PATH = "template_letter"
    if not Letter.check_letter(TEMPLATE_PATH):
        richError("Can't find template letter")
        return
    if letter_name is None:
        letter_name = typer.prompt("Please enter the letter name")
    try:
        shutil.copytree(TEMPLATE_PATH, Path(os.getcwd()) / letter_name)
    except FileExistsError:
        richError("directory already exists")
        return

    richSuccess(f"Letter {letter_name} created")


@app.command()
def check(
    letter_path: str = typer.Argument(
        ..., help="Path to config.ini", exists=True, dir_okay=False,
    ),
):
    """
    check wether a directory is a valid letter, a letter folder should be structured as follows:\n
    letter\n
    ├── attachments\n
    │   ├── ...\n
    │   └── ...\n
    ├── config.yml\n
    ├── content.html\n
    └── recipients.csv\n
    """

    typer.echo("Checking letter")
    if Letter.check_letter(letter_path):
        richSuccess("Letter is valid")
    else:
        richError("Letter is invalid")


if __name__ == "__main__":
    app()
