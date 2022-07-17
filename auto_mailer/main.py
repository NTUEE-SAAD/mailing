##########################################################################
# File:         main.py                                                  #
# Purpose:      Automatically send batch of mails                        #
# Last changed: 2022/07/16                                               #
# Author:       zhuang-jia-xu                                            #
# Edited:                                                                #
# Copyleft:     (ɔ)NTUEE                                                 #
##########################################################################
import typer
from rich import print
from rich.prompt import Confirm, Prompt

import os
import logging
import shutil
from pathlib import Path
from typing import Optional
from configparser import ConfigParser

from .utils import *
from .AutoMailer import AutoMailer
from .Letter import Letter
from .globals import *

app = typer.Typer()


@app.command()
def send(
    letter_path: Optional[str] = typer.Argument(None, help="Path to letter"),
    test: bool = typer.Option(
        False, "--test", "-t", help="Test mode: send mail to yourself"
    ),
    config_path: str = typer.Option(
        CONFIG_PATH,
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
    if not CONFIG_PATH.is_file():
        print("Config file not found, generating a new one...")
        shutil.copy("config-default.ini", CONFIG_PATH)

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
    emails = Letter(letter_path, auto_mailer_config["account"]["name"],)
    auto_mailer.login()
    auto_mailer.send_emails(emails, test=test)
    auto_mailer.check_bounce_backs()
    richSuccess(
        f"{auto_mailer.success_count} / {auto_mailer.total_count} emails sent successfully"
    )


@app.command()
def create(letter_name: Optional[str] = typer.Argument(..., help="Name of letter")):
    """create a new letter from template"""
    print("Creating a new letter")

    TEMPLATE_PATH = "template_letter"
    if not Letter.check_letter(TEMPLATE_PATH):
        richError("Can't find template letter")
        return
    if letter_name is None:
        letter_name = Prompt.ask("Please enter the letter name")
    try:
        shutil.copytree(TEMPLATE_PATH, Path(os.getcwd()) / letter_name)
    except FileExistsError:
        richError("directory already exists")
        return

    richSuccess(f"Letter {letter_name} created")


@app.command()
def check(
    letter_path: str = typer.Argument(
        ..., help="Path to letter directory", exists=True, dir_okay=False,
    ),
):
    """
    check wether a directory is a valid letter\n
    a letter folder should be structured as follows:\n
    letter\n
    ├── attachments\n
    │   ├── ...\n
    │   └── ...\n
    ├── config.yml\n
    ├── content.html\n
    └── recipients.csv\n
    """

    print("Checking letter")
    if Letter.check_letter(letter_path, verbose=True):
        richSuccess("Letter is valid")
    else:
        richError("Letter is invalid")


@app.command()
def config(
    new_config_path: Optional[str] = typer.Option(
        None,
        "--file",
        "-f",
        help="Path to new config file whose content will be copied to config.ini",
        exists=True,
        dir_okay=False,
    ),
    reset: bool = typer.Option(
        False, "--reset", "-r", help="Reset config.ini to default"
    ),
    show: Optional[bool] = typer.Option(False, "--show", "-s", help="Show config.ini"),
):
    """
    configure the auto mailer\n
    a valid config file should have the following structure:\n
    [smtp]\n
    host=smtps.ntu.edu.tw\n
    port=465\n
    timeout=5\n
    [pop3]\n
    host=msa.ntu.edu.tw\n
    port=995\n
    timeout=5\n
    [account]\n
    name=John Doe\n
    """

    if show:
        typer.echo(Path(CONFIG_PATH).read_text())
        return

    if reset:
        shutil.copy("config-default.ini", CONFIG_PATH)
        richSuccess("Config file reset to default")
        return

    APP_DIR.mkdir(parents=True, exist_ok=True)

    if new_config_path is not None:
        if not AutoMailer.validate_config(CONFIG_PATH):
            richError("Invalid config file")
            exit(1)

        shutil.copy(new_config_path, CONFIG_PATH)
        richSuccess(f"Config file copied to {CONFIG_PATH}")
        return

    if not CONFIG_PATH.is_file():
        print(f"Can't find config file at {APP_DIR}")
        shutil.copy("config-default.ini", CONFIG_PATH)
        richSuccess("config.ini created")

    config = AutoMailer.load_mailer_config(CONFIG_PATH)

    for section, vals in config.items():
        for key, value in vals.items():
            print(f"\n{section}.{key} = {value}")
            if Confirm.ask(
                f"Do you want to modify [blue]{section}.{key}[/blue]?", default=False
            ):
                new_value = Prompt.ask(
                    f"Enter new value for [blue]{section}.{key}",
                    password=key == "password",
                )
                config[section][key] = new_value
                richSuccess(f"{section}.{key} updated")

    new_config_parser = ConfigParser()

    for section, vals in config.items():
        new_config_parser[section] = vals

    with open(CONFIG_PATH, "w") as f:
        new_config_parser.write(f)

    richSuccess(f"Config file updated to {CONFIG_PATH}")


if __name__ == "__main__":
    app()
