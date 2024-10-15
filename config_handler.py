import json
import os

CONFIG_FILE = "config.json"

class ConfigHandler:
    def __init__(self):
        self.server_dir = ""
        self.log_output_dir = ""
        self.sql_host = ""
        self.sql_user = ""
        self.sql_database = ""
        self.sql_port = 3306  # Default port for MySQL/MariaDB

    def load_config(self):
        """Load configuration from file."""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as file:
                config = json.load(file)
                self.server_dir = config.get("server_dir", "")
                self.log_output_dir = config.get("log_output_dir", "")
                self.sql_host = config.get("sql_host", "")
                self.sql_user = config.get("sql_user", "")
                self.sql_database = config.get("sql_database", "")
                self.sql_port = config.get("sql_port", 3306)  # Load the port or default to 3306
            return True
        return False

    def save_config(self):
        """Save configuration to file."""
        with open(CONFIG_FILE, "w") as file:
            config = {
                "server_dir": self.server_dir,
                "log_output_dir": self.log_output_dir,
                "sql_host": self.sql_host,
                "sql_user": self.sql_user,
                "sql_database": self.sql_database,
                "sql_port": self.sql_port  # Include port when saving
            }
            json.dump(config, file)

    def set_server_dir(self, directory):
        """Set server directory and save configuration."""
        self.server_dir = directory
        self.save_config()

    def set_log_output_dir(self, directory):
        """Set log output directory and save configuration."""
        self.log_output_dir = directory
        self.save_config()

    def set_sql_config(self, host, user, database, port):
        """Set SQL configuration and save. Ensure port is passed in this method."""
        self.sql_host = host
        self.sql_user = user
        self.sql_database = database
        self.sql_port = port  # Assign port passed as a parameter
        self.save_config()
