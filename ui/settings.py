class SettingsUI:
    def save_last_book(self):
        """Persist the currently opened book."""
        settings = self.settings.load()
        settings["last_book_id"] = self.current_book_id

        self.settings.save(settings)

    def save_settings(self):
        """Persist reader settings."""
        settings = self.settings.load()
        settings["font_size"] = self.font_size
        self.settings.save(settings)