import subprocess
import threading
import time
import psutil  # For process management
import logging
import os
import datetime
import sys

class ServerManager:
    def __init__(self, server_dir=None, crash_log_dir="crash_logs"):
        self.server_dir = server_dir
        self.server_processes = {}  # This will hold the process objects by server name
        self.logger = logging.getLogger(__name__)
        self.monitoring_threads = {}  # Keep track of monitoring threads for each server
        self.crash_log_dir = crash_log_dir
        os.makedirs(self.crash_log_dir, exist_ok=True)  # Ensure the crash log folder exists
        self.server_logs = {}  # Store logs incrementally
    
    def get_timestamp(self):
        """Generate a timestamp for log filenames."""
        return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def set_server_dir(self, directory):
        self.server_dir = directory
        self.logger.info(f"Server directory set to: {self.server_dir}")

    def start_server(self, server_name, output_callback):
        if not self.server_dir:
            output_callback("Server directory not set.")
            return None

        # Check if the server is already running
        if self.is_server_running(server_name):
            output_callback(f"{server_name} is already running.")
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
            # Add creationflags=subprocess.CREATE_NO_WINDOW on Windows to prevent new windows from popping up
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
                universal_newlines=True,
                cwd=self.server_dir,  # Set the working directory
                env=os.environ,  # Pass the current environment variables
                creationflags=creationflags  # Prevent popups on Windows
            )

            # Store the process object for later use (e.g., stopping the server)
            self.server_processes[server_name] = process
            self.server_logs[server_name] = {"stdout": [], "stderr": []}  # Initialize logs

            # Start threads to capture stdout and stderr
            threading.Thread(target=self._capture_output, args=(process.stdout, output_callback, server_name, "stdout"), daemon=True).start()
            threading.Thread(target=self._capture_output, args=(process.stderr, output_callback, server_name, "stderr"), daemon=True).start()

            self.logger.info(f"Started {server_name} using {executable}")

            # Monitor the process and handle crashes or stops
            threading.Thread(target=self.monitor_server, args=(server_name,), daemon=True).start()

            return process

        except Exception as e:
            output_callback(f"Failed to start {server_name}: {str(e)}")
            return None

    def is_server_running(self, server_name):
        """Check if the server is already running by checking process name."""
        executables = {
            "World Server": "xi_world.exe",
            "Search Server": "xi_search.exe",
            "Map Server": "xi_map.exe",
            "Connect Server": "xi_connect.exe"
        }

        executable = executables.get(server_name)
        if not executable:
            return False  # Unknown server

        # Check if any process is running with the name of the executable
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == executable:
                return True
        return False

    def stop_server(self, server_name):
        """Stop the server if it's running and save the log."""
        process = self.server_processes.get(server_name)
        if process and process.poll() is None:  # Ensure the process is still running
            process.terminate()  # Gracefully terminate the process
            process.wait()  # Wait for the process to fully terminate
            self.logger.info(f"{server_name} has been stopped.")
            self.save_log(server_name, "stopped")
        else:
            self.logger.warning(f"No running process found for {server_name}.")

    def save_log(self, server_name, status):
        """Save the logs for the server to the crash or stop log folder."""
        log_file_path = os.path.join(self.crash_log_dir, f"{server_name}_{status}_{self.get_timestamp()}.log")

        if server_name not in self.server_logs:
            return

        # Combine stdout and stderr and save them to a log file
        try:
            with open(log_file_path, 'w') as log_file:
                log_file.write(f"Logs for {server_name} ({status}):\n\n")
                log_file.write("STDOUT:\n" + "\n".join(self.server_logs[server_name]["stdout"]) + "\n")
                log_file.write("STDERR:\n" + "\n".join(self.server_logs[server_name]["stderr"]) + "\n")
            self.logger.info(f"Log saved for {server_name} at {log_file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save log for {server_name}: {e}")

    def monitor_server(self, server_name):
        """Monitor the server process and handle if it crashes or stops."""
        process = self.server_processes.get(server_name)
        if process:
            process.wait()  # Wait for the process to finish
            if process.returncode != 0:
                self.logger.warning(f"{server_name} crashed with exit code {process.returncode}")
                self.save_log(server_name, "crashed")
            else:
                self.save_log(server_name, "stopped")

    def _capture_output(self, pipe, output_callback, server_name, output_type):
        """Capture and log the output from the process's stdout or stderr."""
        try:
            with pipe:
                for line in iter(pipe.readline, ''):
                    output_callback(f"[{server_name}][{output_type.upper()}] {line.strip()}")
                    if server_name in self.server_logs:
                        self.server_logs[server_name][output_type].append(line.strip())
        except Exception as e:
            output_callback(f"Error capturing output from {server_name}: {str(e)}")
