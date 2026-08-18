import json
from pathlib import Path


SETTINGS_FILE = Path("data/settings.json")


class Settings:
    DEFAULT_SETTINGS = {
        "font_size": 20,
        "page_width": 700,
        "dark_mode": False,
        "last_book_id": None,
    }

    def __init__(self):
        SETTINGS_FILE.parent.mkdir(exist_ok=True)

        if not SETTINGS_FILE.exists():
            self.save(self.DEFAULT_SETTINGS)

    def load(self):
        try:
            with open(
                SETTINGS_FILE,
                "r",
                encoding="utf-8"
            ) as f:
                settings = json.load(f)

            for key, value in self.DEFAULT_SETTINGS.items():
                settings.setdefault(key, value)

            return settings

        except (
            json.JSONDecodeError,
            FileNotFoundError
        ):
            return self.DEFAULT_SETTINGS.copy()

    def save(self, settings):
        with open(
            SETTINGS_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                settings,
                f,
                indent=4
            )