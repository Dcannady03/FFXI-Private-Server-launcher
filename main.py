import os
import sys
import tkinter as tk
import logging
from config_handler import ConfigHandler
from server_manager import ServerManager
from resource_monitor import ResourceMonitor
from sql_manager import SQLManager
from gui import GUI
import json

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename='ffxi_server_manager.log',
        filemode='a'
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

def resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller bundle """
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS  # PyInstaller stores path in _MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_version():
    """Load the version from assets/config/version.json, or create it if it doesn't exist."""
    version_file = resource_path("assets/config/version.json")
    default_version = "1.0.5"  # Set your default version here

    # Ensure the directory exists
    os.makedirs(os.path.dirname(version_file), exist_ok=True)

    try:
        # Try opening the version.json file
        with open(version_file, "r") as file:
            data = json.load(file)
            return data.get("version", default_version)
    except FileNotFoundError:
        # If the file does not exist, create it with the default version
        version_data = {"version": default_version}
        with open(version_file, "w") as file:
            json.dump(version_data, file, indent=4)
        return default_version

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting FFXI Server Manager")

    # Load version info
    version = load_version()

    root = tk.Tk()
    config_handler = ConfigHandler()
    config_handler.load_config()
    
    # Initialize managers
    server_manager = ServerManager(config_handler.server_dir)
    resource_monitor = ResourceMonitor()
    sql_manager = SQLManager()

    # Create the GUI, passing in all required managers and version info
    gui = GUI(root, config_handler, server_manager, resource_monitor, sql_manager, version)
    logger.info("GUI initialized, starting main loop")
    root.mainloop()

if __name__ == "__main__":
    main()
