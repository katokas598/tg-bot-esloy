import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_SETTINGS = {
    "welcome_text": "Привет дорогой, {name}",
    "rules_text": "Правила пока не настроены.",
    "admins_text": "Админы пока не настроены.",
    "discord_url": "https://discord.gg/example",
    "tiktok_url": "https://www.tiktok.com/",
    "rules_enabled": "1",
    "admins_enabled": "1",
    "discord_enabled": "1",
    "tiktok_enabled": "1",
}


class Database:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row

    def init(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS commands (
                command TEXT PRIMARY KEY,
                response TEXT NOT NULL
            )
            """
        )
        for key, value in DEFAULT_SETTINGS.items():
            self.connection.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        self.connection.commit()

    def get_setting(self, key: str) -> str:
        row = self.connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            return DEFAULT_SETTINGS.get(key, "")
        return str(row["value"])

    def set_setting(self, key: str, value: str) -> None:
        self.connection.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self.connection.commit()

    def enabled(self, key: str) -> bool:
        return self.get_setting(key) == "1"

    def toggle(self, key: str) -> bool:
        new_value = "0" if self.enabled(key) else "1"
        self.set_setting(key, new_value)
        return new_value == "1"

    def add_command(self, command: str, response: str) -> None:
        self.connection.execute(
            "INSERT INTO commands (command, response) VALUES (?, ?) ON CONFLICT(command) DO UPDATE SET response = excluded.response",
            (command, response),
        )
        self.connection.commit()

    def delete_command(self, command: str) -> bool:
        cursor = self.connection.execute("DELETE FROM commands WHERE command = ?", (command,))
        self.connection.commit()
        return cursor.rowcount > 0

    def get_command(self, command: str) -> str | None:
        row = self.connection.execute("SELECT response FROM commands WHERE command = ?", (command,)).fetchone()
        if row is None:
            return None
        return str(row["response"])

    def list_commands(self) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT command, response FROM commands ORDER BY command").fetchall()
        return [dict(row) for row in rows]
