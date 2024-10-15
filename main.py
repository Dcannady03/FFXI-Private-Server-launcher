import os
import sys
import ctypes
import tkinter as tk
import logging
from config_handler import ConfigHandler
from server_manager import ServerManager
from resource_monitor import ResourceMonitor
from sql_manager import SQLManager  # Assuming this is your SQL manager
from gui import GUI

#def is_admin():
 #   """Check if the script is running with admin rights."""
  #  try:
   #     return ctypes.windll.shell32.IsUserAnAdmin()
    #except:
    # 3   return False

#def run_as_admin():
 #   """Re-launch the script with admin privileges."""
  #  try:
   #     # Re-launch the script with admin rights
   #   ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    #    sys.exit(0)  # Exit the current instance, so the elevated one runs
    #except Exception as e:
     #   print(f"Failed to re-launch as admin: {e}")
      #  sys.exit(1)

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

def main():
    # Check for admin rights and relaunch as admin if not running with elevated privileges
    #if not is_admin():
     #   print("Re-launching with admin privileges")
      #  run_as_admin()

    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting FFXI Server Manager")

    root = tk.Tk()

    # Initialize managers
    config_handler = ConfigHandler()
    config_handler.load_config()

    server_manager = ServerManager(config_handler.server_dir)
    resource_monitor = ResourceMonitor()
    sql_manager = SQLManager()  # Initialize SQLManager or similar

    # Create the GUI, passing in all required managers
    gui = GUI(root, config_handler, server_manager, resource_monitor, sql_manager)

    logger.info("GUI initialized, starting main loop")
    root.mainloop()

if __name__ == "__main__":
    main()
