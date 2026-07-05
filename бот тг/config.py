import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_password: str
    db_path: str


def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Create .env from .env.example and add your bot token.")

    return Config(
        bot_token=bot_token,
        admin_password=os.getenv("ADMIN_PASSWORD", "zZ25255252"),
        db_path=os.getenv("DB_PATH", "bot.db"),
    )
