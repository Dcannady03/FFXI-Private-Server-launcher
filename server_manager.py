import subprocess
import threading
import time
import psutil  # For process management
import logging
import os
import tkinter as tk
import datetime

class ServerManager:
    def __init__(self, server_dir=None):
        self.server_dir = server_dir
        self.server_processes = {}  # This will hold the process objects by server name
        self.logger = logging.getLogger(__name__)
        self.monitoring_threads = {}  # Keep track of monitoring threads for each server
    
    def get_timestamp(self):
        """Generate a timestamp for log filenames."""
        return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def save_server_log(self, server_name):
        """Save the server log to the selected log output directory."""
        # Ensure the ServerManager log directory is set
        if not hasattr(self, 'log_output_dir') or not self.log_output_dir:
            self.logger.warning(f"Log output directory for {server_name} is not set.")
            return

        # Ensure the GUI has log content for the server
        if server_name not in self.gui.server_text_logs:
            self.logger.warning(f"No log content found for {server_name}.")
            return

        # Get the log content from the text widget in the GUI
        log_content = self.gui.server_text_logs[server_name].get("1.0", tk.END)

        # Create the log file name with the server name and timestamp
        log_filename = f"{server_name}_log_{self.get_timestamp()}.txt"
        log_filepath = os.path.join(self.log_output_dir, log_filename)

        try:
            # Save the log content to the file
            with open(log_filepath, 'w') as log_file:
                log_file.write(log_content)
            self.logger.info(f"Log saved for {server_name} at {log_filepath}")
        except Exception as e:
            self.logger.error(f"Error saving log for {server_name}: {e}")

    def set_server_dir(self, directory):
        self.server_dir = directory
        self.logger.info(f"Server directory set to: {self.server_dir}")

    def start_server(self, server_name, output_callback):
        if not self.server_dir:
            output_callback("Server directory not set.")
            return None

        # Map the correct executable based on the server name
        executables = {
            "World Server": "xi_world.exe",
            "Search Server": "xi_search.exe",
            "Map Server": "xi_map.exe",
            "Connect Server": "xi_connect.exe"
        }

        executable = executables.get(server_name)
        if not executable:
            output_callback(f"Unknown server: {server_name}")
            return None

        # Build the command to execute
        command = [f'{self.server_dir}/{executable}']

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
                universal_newlines=True,
                cwd=self.server_dir,  # Set the working directory
                env=os.environ  # Pass the current environment variables
            )

            # Store the process object for later use (e.g., stopping the server)
            self.server_processes[server_name] = process

            # Start threads to capture stdout and stderr
            threading.Thread(target=self._capture_output, args=(process.stdout, output_callback, server_name), daemon=True).start()
            threading.Thread(target=self._capture_output, args=(process.stderr, output_callback, server_name, "ERROR"), daemon=True).start()

            self.logger.info(f"Started {server_name} using {executable}")

            # Return the process so the caller can track it
            # Start monitoring the server process
            threading.Thread(target=self.monitor, args=(server_name,), daemon=True).start()
            return process

        except Exception as e:
            output_callback(f"Failed to start {server_name}: {str(e)}")
            return None


    def monitor(self, server_name):
        """Monitor the server process and restart it if necessary."""
        process = self.server_processes.get(server_name)
        if process is None:
            self.logger.error(f"Process for {server_name} not found.")
            return

        while True:
            if process.poll() is not None:  # Process has stopped
                self.logger.info(f"{server_name} has stopped.")
                self.save_server_log(server_name)  # Save logs when the server stops
                break
            time.sleep(1)  # Adjust the monitoring interval as needed

    def stop_server(self, server_name):
        """Stop the selected server and kill the process."""
        process = self.server_processes.get(server_name)

        if process:
            self.logger.info(f"Stopping {server_name} with PID {process.pid}")
            process.terminate()

            try:
                process.wait(timeout=5)  # Wait for the process to terminate
                self.logger.info(f"{server_name} stopped successfully.")
            except psutil.TimeoutExpired:
                self.logger.warning(f"{server_name} did not terminate in time, force killing.")
                process.kill()  # Forcefully kill the process

            # Remove from tracking
            del self.server_processes[server_name]
        else:
            self.logger.warning(f"No running process found for {server_name}")


    def save_server_log(self, server_name):
        """Save the server log to the selected log output directory."""
        # Ensure the ServerManager log directory is set
        if not hasattr(self, 'log_output_dir') or not self.log_output_dir:
            self.logger.warning(f"Log output directory for {server_name} is not set.")
            return

        # Ensure the GUI has log content for the server
        if server_name not in self.gui.server_text_logs:
            self.logger.warning(f"No log content found for {server_name}.")
            return

        # Get the log content from the text widget in the GUI
        log_content = self.gui.server_text_logs[server_name].get("1.0", tk.END)

        # Create the log file name with the server name and timestamp
        log_filename = f"{server_name}_log_{self.get_timestamp()}.txt"
        log_filepath = os.path.join(self.log_output_dir, log_filename)

        try:
            # Save the log content to the file
            with open(log_filepath, 'w') as log_file:
                log_file.write(log_content)
            self.logger.info(f"Log saved for {server_name} at {log_filepath}")
        except Exception as e:
            self.logger.error(f"Error saving log for {server_name}: {e}")

    def _capture_output(self, stream, output_callback, server_name, prefix=""):
        """Capture the server's stdout/stderr output in real-time."""
        try:
            for line in iter(stream.readline, ''):
                if line:
                    self.logger.info(f"{prefix} {server_name}: {line.strip()}")
                    output_callback(f"{prefix} {server_name}: {line.strip()}")
            stream.close()
        except Exception as e:
            self.logger.error(f"Error capturing output for {server_name}: {e}")
            output_callback(f"Error capturing output for {server_name}: {e}")
