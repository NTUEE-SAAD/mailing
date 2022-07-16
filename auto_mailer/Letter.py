##########################################################################
# File:         Letter.py                                                #
# Purpose:      Automatically send batch of mails                        #
# Last changed: 2015/06/21                                               #
# Author:       zhuang-jia-xu                                            #
# Edited:                                                                #
# Copyleft:     (ɔ)NTUEE                                                 #
##########################################################################
from cerberus import Validator
from email_validator import validate_email, caching_resolver

import os
import csv
import yaml
import re
import logging
from typing import List
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate
from string import Template

from .utils import *

letter_config_schema = {
    "subject": {"type": "string", "required": True},
    "from": {"type": "string"},
    "recipientTitle": {"type": "string"},
    "lastNameOnly": {"type": "boolean"},
    "cc": {"type": "list"},
    "bcc": {"type": "list"},
    "bccToSender": {"type": "boolean"},
}

v = Validator(letter_config_schema)


class Letter:
    paths: dict = None
    config: dict = None
    csv: List = None
    email_addrs: List = None
    emails: List = None

    def __init__(self, letter_path: str, sender_name: str, sender_email: str):
        self.paths = self.__get_paths(letter_path)
        self.config = {
            **self.__load_letter_config(self.paths["config"]),
            "sender_name": sender_name,
            "sender_email": sender_email,
            "attachments": [],
        }

        if os.path.isdir(self.paths["attachments"]):
            attachments = [
                *filter(lambda a: a[0] != ".", os.listdir(self.paths["attachments"]))
            ]
            if len(attachments) > 0:
                self.config["attachments"] = [
                    os.path.join(self.paths["attachments"], a) for a in attachments
                ]

        self.csv = self.__load_recipients()
        self.email_addrs = [row["email"] for row in self.csv]
        self.emails = self.__generate_emails()

    def __get_paths(self, letter_path: str) -> list:
        """get paths of letter"""
        letter_root_path = Path(letter_path)

        paths = {
            "content": letter_root_path / "content.html",
            "config": letter_root_path / "config.yml",
            "attachments": letter_root_path / "attachments",
            "recipients": letter_root_path / "recipients.csv",
        }

        for key, path in paths.items():
            if key == "attachments":
                continue
            if not os.path.exists(path):
                logging.error(f"letter: {path} not found")
                richError(f"letter {key} not found at {path}")

        return paths

    @classmethod
    def validate_letter_dir(cls, letter_path: str) -> bool:
        letter_root_path = Path(letter_path)

        paths = {
            "content": letter_root_path / "content.html",
            "config": letter_root_path / "config.yml",
            "attachments": letter_root_path / "attachments",
            "recipients": letter_root_path / "recipients.csv",
        }

        is_valid = True
        for key, path in paths.items():
            if not path.exists():
                logging.error(f"letter: {path} not found")
                richError(f"letter {key} not found at {path}", terminate=False)
                is_valid = False
            if key == "attachments":
                if not path.is_dir():
                    richError(f"{path} should be a dir", terminate=False)
                    is_valid = False
            else:
                if not path.is_file():
                    richError(f"{path} should be a file", terminate=False)
                    is_valid = False

        return is_valid

    def __load_letter_config(self, path):
        if not Path(path).is_file():
            logging.error(f"{path} is not a file")
            richError(
                f"failed to load letter config at {path}, please enter a valid letter path"
            )

        with open(path, encoding="utf-8") as f:
            letter_config = yaml.load(f, Loader=yaml.FullLoader)

        if v.validate(letter_config):
            letter_config = v.document.copy()
        else:
            logging.critical(f"{path} is not a valid letter config")
            logging.critical(letter_config)
            richError(
                f"letter config validation failed, please check {self.paths['config']}",
                terminate=False,
            )
            parse_validation_error(v._errors)
            exit(1)

        if "cc" in letter_config:
            letter_config["cc"] = letter_config["cc"] = complete_school_email(
                letter_config["cc"]
            )
        if "bcc" in letter_config:
            letter_config["bcc"] = complete_school_email(letter_config["bcc"])

        return letter_config

    @classmethod
    def validate_letter_config(cls, path: str) -> bool:
        with open(path, encoding="utf-8") as f:
            letter_config = yaml.load(f, Loader=yaml.FullLoader)
        return v.validate(letter_config)

    def __load_recipients(self):
        """load recipients from csv file"""
        with open(self.paths["recipients"], encoding="utf-8") as f:
            reader = csv.DictReader(f)
            recipients = [row for row in reader]

        stripped_recipients = []

        has_errors = False
        for row in recipients:
            temp_row = {}
            for i, (key, value) in enumerate(row.items()):
                if key is None:
                    logging.error(
                        f"{self.paths['recipients']} has empty column at row {i}"
                    )
                    richError(
                        f"too many fields at row {i} in {self.paths['recipients']}",
                        terminate=False,
                    )
                    has_errors = True
                    continue
                if (key == "email" or key == "name") and value == "":
                    logging.error(
                        f"{self.paths['recipients']} has empty column at row {i}"
                    )
                    richError(
                        f"empty {key} at row {i} in {self.paths['recipients']}",
                        terminate=False,
                    )
                    has_errors = True
                    continue
                temp_row[key.strip()] = value.strip()
            stripped_recipients.append(temp_row)

        if has_errors:
            logging.error(f"letter csv: {Path(self.paths['recipients']).read_text()}")
            richError(f"failed to load recipients from {self.paths['recipients']}")

        for row in stripped_recipients:
            row["email"] = complete_school_email(row["email"].lower())

        # validate emails
        has_errors = False
        resolver = caching_resolver()
        for i, row in enumerate(stripped_recipients):
            try:
                validate_email(row["email"], dns_resolver=resolver)
            except:
                logging.error(
                    f"{self.paths['recipients']} has invalid email at row {i}"
                )
                richError(
                    f"invalid email {row['email']} detected at row {i} in {self.paths['recipients']}",
                    terminate=False,
                )
                has_errors = True

        if has_errors:
            logging.error(f"letter csv: {Path(self.paths['recipients']).read_text()}")
            richError(f"failed to load recipients from {self.paths['recipients']}")

        return stripped_recipients

    @classmethod
    def validate_recipients(cls, path: str) -> bool:
        """validate recipients"""
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            recipients = [row for row in reader]

        has_errors = False
        stripped_recipients = []
        for row in recipients:
            temp_row = {}
            for i, (key, value) in enumerate(row.items()):
                if key is None:
                    logging.error(f"{path} has empty column at row {i}")
                    richError(
                        f"too many fields at row {i} in {path}", terminate=False,
                    )
                    has_errors = True
                    continue
                if (key == "email" or key == "name") and value == "":
                    logging.error(f"{path} has empty column at row {i}")
                    richError(
                        f"empty {key} at row {i} in {path}", terminate=False,
                    )
                    has_errors = True
                    continue
                temp_row[key.strip()] = value.strip()
            stripped_recipients.append(temp_row)

        if has_errors:
            logging.error(f"letter csv: {Path(path).read_text()}")
            richError(f"failed to load recipients from {path}")

        for row in stripped_recipients:
            row["email"] = complete_school_email(row["email"].lower())

        resolver = caching_resolver()
        for i, row in enumerate(stripped_recipients):
            try:
                validate_email(row["email"], dns_resolver=resolver)
            except:
                logging.error(f"{path} has invalid email at row {i}")
                richError(
                    f"invalid email {row['email']} detected at row {i} in {path}",
                    terminate=False,
                )
                has_errors = True

        if has_errors:
            logging.error(f"letter csv: {Path(path).read_text()}")
            richError(
                f"failed to load recipients from {path}", terminate=False,
            )

        return not has_errors

    def __generate_emails(self):
        """generate emails from csv file"""
        emails = []

        # validate template fields
        email_template = Path(self.paths["content"]).read_text(encoding="utf-8")
        fields = re.findall(r"\$([_a-z][_a-z0-9]*)", email_template, re.M)
        for field in fields:
            if field not in (*self.csv[0].keys(), "sender"):
                logging.error(f"letter template field '{field}' not found in csv")
                logging.error(
                    f"letter template: {Path(self.paths['content']).read_text()}"
                )
                logging.error(
                    f"letter csv: {Path(self.paths['recipients']).read_text()}"
                )
                richError(
                    f"letter template field '{field}' not found in csv, please check {self.paths['content']} and {self.paths['recipients']}"
                )
        email_template = Template(email_template)

        # create attachments
        mime_attachments = []
        for attachment in self.config["attachments"]:
            with open(attachment, "rb") as f:
                mime_attachment = MIMEApplication(
                    f.read(), Name=os.path.basename(attachment)
                )

            mime_attachment[
                "Content-Disposition"
            ] = f"attachment; filename={os.path.basename(attachment)}"

            mime_attachments.append(mime_attachment)

        for recipient in self.csv:
            email = self.__generate_email(recipient, email_template, mime_attachments)
            emails.append(email)
        return emails

    @classmethod
    def validate_email_content(cls, content_path: str, csv_path: str) -> bool:
        """validate email content"""
        email_template = Path(content_path).read_text(encoding="utf-8")
        fields = re.findall(r"\$([_a-z][_a-z0-9]*)", email_template, re.M)
        is_valid = True
        with open(csv_path, encoding="utf-8") as f:
            line = f.readline()
        line = line.split(",")
        line = [i.strip() for i in line] + ["sender"]
        for field in fields:
            if field not in line:
                logging.error(f"letter template field '{field}' not found in csv")
                is_valid = False

        return is_valid

    def __generate_email(
        self,
        recipient: dict,
        email_template: Template,
        mime_attachments: List[MIMEApplication],
    ):
        """generate email from recipient"""

        email = MIMEMultipart()
        email["Date"] = formatdate(localtime=True)

        email["Subject"] = self.config["subject"]

        email["To"] = recipient["email"]

        if "from" in self.config:
            email["From"] = formataddr(
                (self.config["from"], self.config["sender_email"])
            )

        if "cc" in self.config:
            email["Cc"] = ",".join(self.config["cc"])

        if "bcc" in self.config:
            if self.config["bccToSender"]:
                bccs = [*self.config["bcc"], self.config["sender_email"]]
                email["Bcc"] = ",".join(bccs)
            else:
                email["Bcc"] = ",".join(self.config["bcc"])
        elif "bccToSender" in self.config and self.config["bccToSender"]:
            email["Bcc"] = self.config["sender_email"]

        if "recipientTitle" in self.config:
            if "lastNameOnly" in self.config and self.config["lastNameOnly"]:
                # only supports chinese names
                recipient["name"] = recipient["name"][0]
            recipient["name"] = recipient["name"] + self.config["recipientTitle"]

        email.attach(
            MIMEText(
                email_template.substitute(
                    {**recipient, "sender": self.config["sender_name"]}
                ),
                "html",
            )
        )

        for mime_attachment in mime_attachments:
            email.attach(mime_attachment)

        return email

    def __iter__(self):
        return iter(self.emails)

    def __len__(self):
        return len(self.emails)

    @classmethod
    def check_letter(cls, letter_path: str) -> bool:
        """check letter"""
        is_valid = True

        is_valid &= cls.validate_letter_dir(letter_path)
        if not is_valid:
            return False

        is_valid &= cls.validate_letter_config(Path(letter_path) / "config.yml")

        is_valid &= cls.validate_recipients(Path(letter_path) / "recipients.csv")
        if not is_valid:
            return False

        is_valid &= cls.validate_email_content(
            Path(letter_path) / "content.html", Path(letter_path) / "recipients.csv"
        )

        return is_valid
