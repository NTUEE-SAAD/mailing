##########################################################################
# File:         AutoMailer.py                                            #
# Purpose:      Automatically send batch of mails                        #
# Last changed: 2015/06/21                                               #
# Author:       zhuang-jia-xu                                            #
# Edited:                                                                #
# Copyleft:     (ɔ)NTUEE                                                 #
##########################################################################
from rich import print
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    BarColumn,
)
from cerberus import Validator

import time
import os
import re
import logging
from typing import List
from configparser import ConfigParser
from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
import poplib
from email.parser import Parser as EmailParser

from .utils import *
from .Letter import Letter

auto_mailer_config_schema = {
    "account": {
        "type": "dict",
        "require_all": True,
        "schema": {
            "userid": {"type": "string"},
            "password": {"type": "string"},
            "name": {"type": "string"},
        },
    },
    "smtp": {
        "require_all": True,
        "type": "dict",
        "schema": {
            "host": {"type": "string"},
            "port": {"type": "integer", "coerce": int},
            "timeout": {"type": "integer", "coerce": int},
        },
    },
    "pop3": {
        "require_all": True,
        "type": "dict",
        "schema": {
            "host": {"type": "string"},
            "port": {"type": "integer", "coerce": int},
            "timeout": {"type": "integer", "coerce": int},
        },
    },
}
v = Validator(auto_mailer_config_schema, require_all=True)

email_re = re.compile("[a-z0-9-_\.]+@[a-z0-9-\.]+\.[a-z\.]{2,5}")


class AutoMailer:
    verbose: bool = True
    SMTPserver: smtplib.SMTP_SSL = None
    config: dict = None
    count: int = 0
    success_count: int = 0
    email_addrs: List[str] = []

    def __init__(self, config: dict = None, quiet: bool = False) -> None:
        self.config = config
        self.verbose = not quiet

    def connect(self) -> None:
        """connect to SMTP server"""
        self.SMTPserver = self.__createSMTPServer(
            self.config["account"]["userid"], self.config["account"]["password"]
        )

    def send_emails(self, letter: Letter, test: bool = False) -> None:
        """send emails"""
        if self.verbose:
            print("-" * 50)
            print(Path(letter.paths["content"]).read_text())
            print("-" * 50)
            if not typerConfirm(
                "Are you sure to send emails with the content above?", countdown=3,
            ):
                logging.info("User cancelled on checking content")
                richError("Canceled", prefix="")

        if not typerConfirm(
            f"Are you sure to send email{'s' if len(letter) > 1 else ''} to {len(letter)} recipients?\n(please use test mode before you send emails)",
        ):
            logging.info("User cancelled on sending emails")
            richError("Canceled", prefix="")

        if self.SMTPserver is None:
            logging.info("SMTP server is not connected, please connect first")
            richError("SMTP server is not connected, please connect first")

        # only send one email in test mode
        if test:
            letter = [*letter][:1]

        self.email_addrs += letter.email_addrs

        progress = Progress(
            TextColumn("[bold blue]{task.description}", justify="right"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.completed} of {task.total:.0f}",
            "•",
            TimeRemainingColumn(),
        )

        with progress:
            logging.info(f"Sending {len(letter)} emails")
            for email in progress.track(letter, description="Sending emails..."):
                if test:
                    email["To"] = complete_school_email(
                        self.config["account"]["userid"]
                    )
                success = self.send_email(email)
                if success:
                    self.success_count += 1
                    if self.verbose:
                        progress.print(
                            f"[green]successfully sent email to {email['To']}"
                        )
                else:
                    progress.print(f'[red]failed to send email to {email["To"]}')
                self.__server_rest()

    def send_email(self, email: MIMEMultipart) -> None:
        """send email"""
        if self.SMTPserver is None:
            richError("SMTP server is not connected, please connect first")

        self.count += 1

        toaddrs = email["To"].split(",")
        ccaddrs = email["Cc"].split(",") if email["Cc"] is not None else []
        bccaddrs = email["Bcc"].split(",") if email["Bcc"] is not None else []

        try:
            self.SMTPserver.sendmail(
                email["From"], toaddrs + ccaddrs + bccaddrs, email.as_string(),
            )
        except Exception as e:
            logging.error(e)
            logging.error(f"Failed to send email to {email['To']}")
            return False

        logging.info(f"Sent email {toaddrs}")

        return True

    def check_bounce_backs(self) -> None:
        """show help message if emails are bounced back, this usually happens when trying to email a wrong school email address"""
        logging.info("Checking bounce backs")
        progress = Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        )
        with progress:
            progress.add_task(description="checking for bounce-backs...", total=None)
            time.sleep(5)  # wait for bounce back

            try:
                # connect to pop3 server
                pop3 = poplib.POP3_SSL(
                    host=self.config["pop3"]["host"],
                    port=self.config["pop3"]["port"],
                    timeout=self.config["pop3"]["timeout"],
                )
                pop3.user(self.config["account"]["userid"])
                pop3.pass_(self.config["account"]["password"])
            except Exception as e:
                logging.error(e)
                logging.error("Failed to connect to pop3 server")
                progress.print("[red]Failed to connect to pop3 server")
                return 0

            progress.print("Connected to POP3 server")
            logging.info("Connected to POP3 server")
            # retrieve last n emails
            _, mails, _ = pop3.list()
            emails = [
                pop3.retr(i)[1]
                for i in range(len(mails), len(mails) - len(self.email_addrs), -1)
            ]
            pop3.quit()

            email_contents = []
            # Concat message pieces:
            for mssg in emails:
                # some chinese character may not be able to parse,
                # however, we only care about the bounce back notifications,
                # which are alays in English
                try:
                    email_contents.append(b"\r\n".join(mssg).decode("utf-8"))
                except:
                    continue

            # Parse message into an email object:
            email_contents = [
                EmailParser().parsestr(content, headersonly=True)
                for content in email_contents
            ]

            bounced_list = []

            for content in email_contents:
                if not re.match(
                    "(Delivery Status Notification)|(Undelivered Mail Returned to Sender)",
                    content["subject"],
                ):
                    continue

                # match for email addresses
                addr = email_re.search(content.get_payload()).group()
                bounced_list.append(addr)

            bounced_list = list(filter(lambda x: x in self.email_addrs, bounced_list))

            if len(bounced_list) > 0:
                progress.print(
                    "[red]Emails sent to these addresses are bounced back (failed):"
                )
                for address in bounced_list:
                    progress.print(f"\t{address},")
                progress.print("[red]Please check these emails.")
            else:
                progress.print(
                    "[green]No bounce-backs found, all emails are delivered successfully",
                )

        richSuccess(
            f"{self.success_count}/{len(self.email_addrs)} emails sent successfully"
        )

    def __server_rest(self):
        """for bypassing email server limitation"""

        if self.count % 10 == 0 and self.count > 0:
            print("resting...")
            time.sleep(10)
        if self.count % 130 == 0 and self.count > 0:
            print("resting...")
            time.sleep(20)
        if self.count % 260 == 0 and self.count > 0:
            print("resting...")
            time.sleep(20)

    def __createSMTPServer(self, userid, password) -> smtplib.SMTP_SSL:
        """create SMTP server"""

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Connecting to SMTP Server...", total=None)

            time.sleep(1)

            try:
                server = smtplib.SMTP_SSL(
                    host=self.config["smtp"]["host"],
                    port=self.config["smtp"]["port"],
                    timeout=self.config["smtp"]["timeout"],
                )
            except Exception as e:
                logging.critical(e)
                logging.critical("Failed to connect to SMTP server")
                richError("Failed to connect to SMTP server")

            if server.has_extn("STARTTLS"):
                server.starttls()
            server.ehlo()

            try:
                server.login(userid, password)
            except:
                logging.critical("Failed to login to SMTP server")
                richError(
                    "SMTP login failed, please check your account info in config.ini"
                )

        logging.info("Connected to SMTP server")
        richSuccess("SMTP server connected")

        return server

    @classmethod
    def load_mailer_config(cls, config_path: str) -> dict:
        """load auto mailer configuration from config.ini"""
        config_path = Path(config_path)
        automailer_config = ConfigParser()
        if not os.path.exists(config_path):
            richError(f"{config_path} not found")

        automailer_config.read({config_path}, encoding="utf-8")

        sections = automailer_config.sections()

        config = {}

        for section in sections:
            options = automailer_config.options(section)
            temp_dict = {}
            for option in options:
                temp_dict[option] = automailer_config.get(section, option)

            config[section] = temp_dict

        if v.validate(config):
            return v.document.copy()
        else:
            logging.critical(
                f"mailer config validation failed, please check {config_path}"
            )
            logging.critical(config)
            richError(
                f"mailer config validation failed, please check {config_path}",
                terminate=False,
            )
            parse_validation_error(v._errors)
            exit(1)


if __name__ == "__main__":
    auto_mailer_config = AutoMailer.load_mailer_config("config.ini")
    auto_mailer = AutoMailer(auto_mailer_config)
    emails = Letter(
        "letters/test",
        auto_mailer_config["account"]["name"],
        complete_school_email(auto_mailer_config["account"]["userid"]),
    )
    auto_mailer.connect()
    auto_mailer.send_emails(emails)
    auto_mailer.check_bounce_backs()