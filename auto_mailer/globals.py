import typer
from pathlib import Path

APP_NAME = "auto-mailer"
APP_DIR = Path(typer.get_app_dir(APP_NAME))
CONFIG_PATH = Path(APP_DIR) / "config.ini"
