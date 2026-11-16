"""Where the bot token and the data file are."""

import os

from dotenv import load_dotenv

# This file is in the project root, next to the data folder.
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(ROOT, "data", "carswanted.json")


class Config:
    def __init__(self, bot_token, data_path):
        self.bot_token = bot_token
        self.data_path = data_path


def load_config():
    load_dotenv(os.path.join(ROOT, ".env"))
    token = os.getenv("BOT_TOKEN", "")
    if token == "":
        raise SystemExit("BOT_TOKEN is missing. Add it to the .env file in the project root.")
    if not os.path.isfile(DATA_PATH):
        raise SystemExit("Data file not found: " + DATA_PATH)
    return Config(token, DATA_PATH)
