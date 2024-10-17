import json
import os
import sys

CONFIG_FILE = "config.json"

class ConfigHandler:
    def __init__(self):
        self.config_file_path = "assets/config/config.json"  # Set the default path here
        self.server_dir = ""
        self.log_output_dir = ""
        self.sql_host = ""
        self.sql_user = ""
        self.sql_database = ""
        self.sql_port = 3306  # Default port for MySQL/MariaDB
        self.auto_start_servers = False  # Default to False for auto-start servers
        self.text_color = "#ffffff"  # Default text color
        self.bg_color = "#1e1e1e"  # Default background color
        

    def load_config(self):
        """Load configuration from file."""
        if os.path.exists(self.config_file_path):
            with open(self.config_file_path, "r") as file:
                config = json.load(file)
                self.server_dir = config.get("server_dir", "")
                self.log_output_dir = config.get("log_output_dir", "")
                self.sql_host = config.get("sql_host", "")
                self.sql_user = config.get("sql_user", "")
                self.sql_database = config.get("sql_database", "")
                self.sql_port = config.get("sql_port", 3306)  # Load the port or default to 3306
                self.auto_start_servers = config.get("auto_start_servers", False)
                self.text_color = config.get("text_color", "#ffffff")
                self.bg_color = config.get("bg_color", "#1e1e1e")
            return True
        else:
            self.text_color = "#ffffff"
            self.bg_color = "#1e1e1e"
        return False

    def save_config(self):
        """Save the configuration to file."""
    
        # Ensure the directory exists
        config_dir = os.path.dirname(self.config_file_path)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        # Prepare the config dictionary
        config = {
            "server_dir": self.server_dir,
            "log_output_dir": self.log_output_dir,
            "sql_host": self.sql_host,
            "sql_user": self.sql_user,
            "sql_database": self.sql_database,
            "sql_port": self.sql_port,
            "auto_start_servers": self.auto_start_servers,
            "text_color": self.text_color,
            "bg_color": self.bg_color
        }

        # Save the config to file
        with open(self.config_file_path, "w") as configfile:
            json.dump(config, configfile, indent=4)

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

    def set_auto_start_servers(self, value):
        """Set the auto-start servers option and save the config."""
        self.auto_start_servers = value
        self.save_config()

    def get_auto_start_servers(self):
        """Get the current auto-start servers value."""
        return self.auto_start_servers

    def set_color_preferences(self, text_color, bg_color):
        """Save the selected text and background colors to the config file."""
        self.text_color = text_color
        self.bg_color = bg_color
        self.save_config()

    def get_color_preferences(self):
        """Retrieve the saved text and background colors from the config."""
        return self.text_color, self.bg_color

    def resource_path(relative_path):
        """ Get the absolute path to the resource, works for dev and for PyInstaller bundle """
        if hasattr(sys, '_MEIPASS'):
            # If running from a PyInstaller bundle, use the unpacked temp path
            base_path = sys._MEIPASS
        else:
            # If running in dev mode, use the current path
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)