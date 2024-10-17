import os
from pickle import FALSE
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import threading
import logging
from PIL import Image, ImageTk
import psutil  # For resource monitoring
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
from datetime import datetime
import mysql.connector
import tkinter.colorchooser as colorchooser
import sys
import tkinter.messagebox as messagebox
import subprocess
from updater import check_and_update, get_local_version, is_newer_version, download_and_install_update
import json

class GUI:
    def __init__(self, root, config_handler, server_manager, resource_monitor, sql_manager, version):
        self.root = root
        self.config_handler = config_handler
        self.server_manager = server_manager
        self.resource_monitor = resource_monitor
        self.sql_manager = sql_manager
        self.version = version  # Store the version

        self.log_output_dir = self.config_handler.log_output_dir or "No directory selected"
        self.monitoring_threads = {}  # Keep track of monitoring threads for each server
        self.sql_manager.gui = self
        self.server_manager.gui = self

        self.setup_menu_bar() 
        
        # Set the window title with version
        self.root.title(f"FFXI Server Manager (Version {self.version})")

        # Initialize dictionaries for restart checkboxes and server logs
        self.restart_checkboxes = {}
        self.server_text_logs = {}
        self.server_tabs = {}

        # Load icons for server buttons
        self.load_icons()

        # Load SQL connection status GIFs (IMPORTANT)
        self.load_sql_status_icons()  # Ensure this is called here

        # Set up the GUI layout with tabs
        self.setup_layout()

        # Load saved color preferences from config after layout is set up
        self.current_text_color = self.config_handler.text_color
        self.current_bg_color = self.config_handler.bg_color

        # Apply the saved colors after the layout is initialized
        self.apply_text_color(self.current_text_color)
        self.apply_background_color(self.current_bg_color)

        if self.auto_start_servers_var.get():
            self.start_all_servers()  # Auto-start servers if the checkbox is selected
            
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
       
    def add_auto_restart_and_directories(self):
        """Add restart checkboxes and directory selection buttons to the sidebar."""
        # Initialize BooleanVars for each server's checkbox if they aren't initialized already
        if not self.restart_checkboxes:
            self.restart_checkboxes = {
                "World Server": tk.BooleanVar(value=True),
                "Search Server": tk.BooleanVar(value=True),
                "Connect Server": tk.BooleanVar(value=True),
                "Map Server": tk.BooleanVar(value=True),
            }

        # Create the checkboxes for each server
        for server in self.restart_checkboxes:
            checkbox = tk.Checkbutton(
                self.sidebar, text=f"Auto-Restart {server}",
                variable=self.restart_checkboxes[server],
                bg='#555555', fg='black',
                onvalue=True, offvalue=False
            )
            checkbox.pack(pady=5, anchor="w")

        # Load the auto-start setting from the config
        saved_auto_start_value = self.config_handler.get_auto_start_servers()

        # Add a checkbox for auto-starting servers when the program loads
        self.auto_start_servers_var = tk.BooleanVar(value=saved_auto_start_value)  # Load from config
        self.auto_start_checkbox = tk.Checkbutton(
            self.sidebar, text="Auto-Start Servers on Load",
            variable=self.auto_start_servers_var,
            bg='#555555', fg='black',
            onvalue=True, offvalue=False,
            command=self.save_auto_start_setting  # Save setting on toggle
        )
        self.auto_start_checkbox.pack(pady=5, anchor="w")

    def save_auto_start_setting(self):
        """Save the auto-start setting to the config."""
        auto_start_value = self.auto_start_servers_var.get()
        self.config_handler.set_auto_start_servers(auto_start_value)
        
    def on_closing(self):
        """Handle cleanup on application exit."""
        # Stop all servers before exiting
        self.stop_all_servers()

        # Any other cleanup (e.g., saving settings, logs, etc.)
        self.log_message("Shutting down FFXI Server Manager...")
        self.save_auto_start_setting()
        # Destroy the main window (close the application)
        self.root.quit()  # Use `quit()` to ensure the entire application shuts down
        self.root.destroy()

    def resource_path(self, relative_path):
        """ Get the absolute path to the resource, works for dev and for PyInstaller bundle """
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller creates a temporary folder and stores the path in _MEIPASS
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    # Example usage to load an icon
    #icon_path = resource_path('assets/images/icon.png')
    def load_sql_status_icons(self):
        """Load images used for connection status (animated GIFs for both connected and disconnected)."""
        try:
            # Load the connected GIF and store the frames
            self.connected_gif = Image.open(self.resource_path("assets/images/connected.gif"))
            self.connected_gif_frames = []
            for frame_index in range(self.get_gif_frame_count(self.connected_gif)):
                self.connected_gif.seek(frame_index)
                frame = self.connected_gif.copy().resize((30, 30)).convert('RGBA')
                self.connected_gif_frames.append(ImageTk.PhotoImage(frame))

            # Load the disconnected GIF and store the frames
            self.disconnected_gif = Image.open(self.resource_path("assets/images/disconnected.gif"))
            self.disconnected_gif_frames = []
            for frame_index in range(self.get_gif_frame_count(self.disconnected_gif)):
                self.disconnected_gif.seek(frame_index)
                frame = self.disconnected_gif.copy().resize((30, 30)).convert('RGBA')
                self.disconnected_gif_frames.append(ImageTk.PhotoImage(frame))

            # Initialize frame index for animation
            self.gif_frame_index = 0
            self.current_gif_frames = self.disconnected_gif_frames  # Default to disconnected GIF
        except Exception as e:
            logging.error(f"Error loading status icons: {e}")


    
    def get_gif_frame_count(self, gif_image):
        """Helper function to get the number of frames in a GIF."""
        frame_count = 0
        try:
            while True:
                gif_image.seek(frame_count)
                frame_count += 1
        except EOFError:
            pass  # Reached the end of the GIF
        return frame_count        
    
    
    def animate_sql_status(self):
        """Animate the connection status icon using the current GIF frames."""
        if hasattr(self, 'current_gif_frames') and self.current_gif_frames:
            frame = self.current_gif_frames[self.gif_frame_index]
            self.sql_status_icon.config(image=frame)

            # Update the frame index
            self.gif_frame_index = (self.gif_frame_index + 1) % len(self.current_gif_frames)

            # Continue the animation after 100 milliseconds
            self.root.after(160, self.animate_sql_status)



    

    def clear_results(self):
        """Clear any unread results before executing a new query."""
        if self.connection and self.connection.unread_result:
           self.connection.get_rows()  # Fetch all remaining results to clear the unread state


    def load_icons(self):
        """Load images used for server buttons and actions."""
        self.world_icon = ImageTk.PhotoImage(Image.open(self.resource_path("assets/images/world_icon.png")).resize((60, 60)))
        self.search_icon = ImageTk.PhotoImage(Image.open(self.resource_path("assets/images/search_icon.png")).resize((60, 60)))
        self.map_icon = ImageTk.PhotoImage(Image.open(self.resource_path("assets/images/map_icon.png")).resize((60, 60)))
        self.connect_icon = ImageTk.PhotoImage(Image.open(self.resource_path("assets/images/connect_icon.png")).resize((60, 60)))
        self.start_icon = ImageTk.PhotoImage(Image.open(self.resource_path("assets/images/start_icon.png")).resize((60, 60)))
        self.stop_icon = ImageTk.PhotoImage(Image.open(self.resource_path("assets/images/stop_icon.png")).resize((60, 60)))

    def update_sql_status_icon(self, connected):
        """Update the connection status icon based on the connection state."""
        if connected:
            self.current_gif_frames = self.connected_gif_frames  # Use connected GIF frames
        else:
            self.current_gif_frames = self.disconnected_gif_frames  # Use disconnected GIF frames

        # Start animating from the first frame of the selected GIF
        self.gif_frame_index = 0
        self.animate_sql_status()


    def setup_layout(self):
        """Create the overall layout of the GUI with tabs."""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Main Control Tab
        self.main_tab = tk.Frame(self.notebook, bg='#1e1e1e')
        self.notebook.add(self.main_tab, text='Main Control')

        # Resource Monitoring Tab
        #self.resource_tab = tk.Frame(self.notebook, bg='#1e1e1e')
        #self.notebook.add(self.resource_tab, text='Resources')

        # SQL Management Tab
        self.sql_tab = tk.Frame(self.notebook, bg='#1e1e1e')
        self.notebook.add(self.sql_tab, text='SQL Management')

        self.setup_main_tab()
        #self.setup_resource_tab()
        self.setup_sql_tab()

    def setup_main_tab(self):
        """Configure the Main Control Tab for server management."""
        # Sidebar for server buttons
        self.sidebar = tk.Frame(self.main_tab, width=200, bg='#333333')
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)

        self.exit_icon = ImageTk.PhotoImage(Image.open(self.resource_path("assets/images/exit.png")).resize((60, 60)))

        # Add the exit button at the bottom of the sidebar
        self.exit_button = tk.Button(
            self.sidebar, image=self.exit_icon, command=self.on_closing, bg='#dc3545', fg='#ffffff'
        )
        self.exit_button.pack(side=tk.BOTTOM, pady=10)

        # Add a label below the button that says "Stop Servers and Exit"
        self.exit_label = tk.Label(self.sidebar, text="Stop Servers and Exit", bg='#333333', fg='#ffffff')
        self.exit_label.pack(side=tk.BOTTOM, pady=5)
               

        # Notebook for server-specific tabs (each server gets its own tab)
        self.server_notebook = ttk.Notebook(self.main_tab)
        self.server_notebook.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Create buttons for each server and its corresponding tab
        self.add_server_buttons()
        self.add_auto_restart_and_directories()
        
    def setup_menu_bar(self):
        """Create the menu bar with Exit and Settings options."""
        menu_bar = tk.Menu(self.root)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.on_closing)
        menu_bar.add_cascade(label="File", menu=file_menu)

        settings_menu = tk.Menu(menu_bar, tearoff=0)
        settings_menu.add_command(label="Settings", command=self.open_settings)
        menu_bar.add_cascade(label="Settings", menu=settings_menu)

        self.root.config(menu=menu_bar)

    def open_settings(self):
        """Open the settings window for customizing colors."""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x400")
        settings_window.attributes('-topmost', True)
        self.settings_window = settings_window

        tk.Label(settings_window, text="Customize Colors", font=("Arial", 14)).pack(pady=10)

        # Button to choose text color
        tk.Button(settings_window, text="Choose Text Color", command=self.choose_text_color).pack(pady=5)

        # Button to choose background color for the notebook
        tk.Button(settings_window, text="Choose Notebook Background Color", command=self.choose_background_color).pack(pady=5)
        # Separator
        ttk.Separator(settings_window, orient="horizontal").pack(fill="x", pady=10)

        tk.Label(settings_window, text="Server Directory", font=("Arial", 12)).pack(pady=5)

        # Text box to display and edit the current saved server directory
        self.server_dir_entry = tk.Entry(settings_window, width=50)
        self.server_dir_entry.insert(0, self.server_manager.server_dir or "No directory selected")
        self.server_dir_entry.pack(pady=5)

        # Button to choose server directory
        tk.Button(settings_window, text="Browse...", command=self.choose_server_directory).pack(pady=5)

        tk.Label(settings_window, text="Log Output Folder", font=("Arial", 12)).pack(pady=5)

        # Text box to display and edit the current saved log output folder
        self.log_output_dir_entry = tk.Entry(settings_window, width=50)
        self.log_output_dir_entry.insert(0, self.log_output_dir or "No directory selected")
        self.log_output_dir_entry.pack(pady=5)

        # Button to choose log output directory
        tk.Button(settings_window, text="Browse...", command=self.choose_log_directory).pack(pady=5)
         # Add 'Check for Updates' button
        tk.Button(settings_window, text="Check for Updates", command=check_and_update).pack(pady=20)
    

   


    def choose_text_color(self):
        """Open the color palette to select the text color."""
        self.settings_window.attributes('-topmost', False)
        color = colorchooser.askcolor(title="Choose Text Color", parent=self.settings_window)[1]  # Get the hex color code  # Get the hex color code
        
        if color:
            self.apply_text_color(color)

        self.settings_window.attributes('-topmost', True)
        self.settings_window.lift()  # Bring the settings window to the front

    def choose_background_color(self):
        """Open the color palette to select the notebook background color."""
        self.settings_window.attributes('-topmost', False)
        color = colorchooser.askcolor(title="Choose Background Color", parent=self.settings_window)[1]  # Get the hex color code
    
        
        if color:
            self.apply_background_color(color)

          # Re-enable 'topmost' and bring the settings window back to the front
        self.settings_window.attributes('-topmost', True)
        self.settings_window.lift()  # Bring the settings window to the front
        
    def apply_text_color(self, color):
        """Apply the selected text color to the text widgets and save the choice."""
        for server_name in self.server_text_logs:
            self.server_text_logs[server_name].config(fg=color)  # Change text color
        self.config_handler.set_color_preferences(text_color=color, bg_color=self.current_bg_color)

    def apply_background_color(self, color):
        """Apply the selected background color to the notebook and save the choice."""
        for server_name in self.server_text_logs:
            self.server_text_logs[server_name].config(bg=color)  # Change the background of the text area
        self.current_bg_color = color  # Save current bg color
        self.config_handler.set_color_preferences(text_color=self.current_text_color, bg_color=color)
         
        
    def add_auto_restart_and_directories(self):
        """Add restart checkboxes and directory selection buttons to the sidebar."""
        # Initialize BooleanVars for each server's checkbox if they aren't initialized already
        if not self.restart_checkboxes:
            self.restart_checkboxes = {
                "World Server": tk.BooleanVar(value=True),
                "Search Server": tk.BooleanVar(value=True),
                "Connect Server": tk.BooleanVar(value=True),
                "Map Server": tk.BooleanVar(value=True),
            }
    
         # Create the checkboxes for each server
        for server in self.restart_checkboxes:
            checkbox = tk.Checkbutton(
                self.sidebar, text=f"Auto-Restart {server}",
                variable=self.restart_checkboxes[server],
                bg='#555555', fg='black',
                onvalue=True, offvalue=False
            )
            checkbox.pack(pady=5, anchor="w")

        saved_auto_start_value = self.config_handler.get_auto_start_servers()
        # Add a checkbox for auto-starting servers when the program loads
        self.auto_start_servers_var = tk.BooleanVar(value=saved_auto_start_value)  # Load from config
        self.auto_start_checkbox = tk.Checkbutton(
            self.sidebar, text="Auto-Start Servers on Load",
            variable=self.auto_start_servers_var,
            bg='#555555', fg='black',
            onvalue=True, offvalue=False,
            command=self.save_auto_start_setting  # Save setting on toggle
        )
        self.auto_start_checkbox.pack(pady=5, anchor="w")
   
        # Start All and Stop All buttons
        self.start_all_button = tk.Button(self.sidebar, text="Start All Servers", command=self.start_all_servers, bg='#28a745', fg='#ffffff')
        self.start_all_button.pack(pady=10, fill=tk.X)

        self.stop_all_button = tk.Button(self.sidebar, text="Stop All Servers", command=self.stop_all_servers, bg='#dc3545', fg='#ffffff')
        self.stop_all_button.pack(pady=10, fill=tk.X)

    def choose_server_directory(self):
        """Prompt the user to select the server directory and update the settings window."""
        self.settings_window.attributes('-topmost', False)
        directory = filedialog.askdirectory(parent=self.settings_window)
        

        if directory:
            self.server_manager.set_server_dir(directory)
            self.log_message(f"Server directory set to: {directory}")
            self.server_dir_entry.delete(0, tk.END)  # Clear the text box
            self.server_dir_entry.insert(0, directory)  # Update the text box with the new path
        
        self.settings_window.attributes('-topmost', True)
        self.settings_window.lift()  # Bring the settings window to the front
        

    def choose_log_directory(self):
        """Prompt the user to select the log output folder and update the settings window."""
        # Temporarily disable 'topmost' for the settings window to allow file dialog
        self.settings_window.attributes('-topmost', False)

        # Open the directory dialog and make it topmost
        directory = filedialog.askdirectory(parent=self.settings_window)
    
        if directory and os.access(directory, os.W_OK):
            self.log_output_dir = directory
            self.server_manager.log_output_dir = directory
            self.log_message(f"Log output folder set to: {directory}")
            self.log_output_dir_entry.delete(0, tk.END)  # Clear the text box
            self.log_output_dir_entry.insert(0, directory)  # Update the text box with the new path

            # Save the log output directory to the config file
            self.config_handler.set_log_output_dir(directory)
        else:
            self.log_message("Invalid directory or write permission issue.")

        # Re-enable 'topmost' for settings window after directory dialog is closed
        self.settings_window.attributes('-topmost', True)
        self.settings_window.lift()  # Bring settings window back to the front

    def add_server_buttons(self):
        """Create buttons for starting and stopping each server and initialize their tabs."""
        servers_with_icons = [
            ("World Server", self.world_icon, self.stop_world_server),
            ("Search Server", self.search_icon, self.stop_search_server),
            ("Map Server", self.map_icon, self.stop_map_server),
            ("Connect Server", self.connect_icon, self.stop_connect_server),
    ]

        for server_name, icon, stop_function in servers_with_icons:
            # Create a button for each server in the sidebar
            tk.Button(
                self.sidebar, image=icon, text=server_name,
                compound=tk.LEFT,  # Combines icon and text
                command=lambda s=server_name: self.switch_to_server_tab(s),  # Switch to the server tab
                bg='#555555', fg='white'
            ).pack(pady=10)

            # Create a new tab for each server in the notebook
            server_frame = tk.Frame(self.server_notebook, bg='#1e1e1e')
            self.server_tabs[server_name] = server_frame
            self.server_notebook.add(server_frame, text=server_name)

            # Add a text log area for each server in its respective tab
            self.server_text_logs[server_name] = ScrolledText(
                server_frame, height=20, width=60, bg='#2e2e2e', fg='#ffffff', insertbackground='#ffffff'
            )
            self.server_text_logs[server_name].pack(fill=tk.BOTH, expand=True)

            # Add start/stop buttons for each server tab
            button_frame = tk.Frame(server_frame, bg='#1e1e1e')
            button_frame.pack(fill=tk.X, pady=5)

            start_button = tk.Button(button_frame, image=self.start_icon, command=lambda s=server_name: self.start_server(s), bg='#28a745')
            start_button.pack(side=tk.LEFT, padx=5, pady=5)

            stop_button = tk.Button(button_frame, image=self.stop_icon, command=stop_function, bg='#dc3545')
            stop_button.pack(side=tk.LEFT, padx=5, pady=5) 

    def switch_to_server_tab(self, server_name):
        """Switch to the tab for the selected server."""
        if server_name in self.server_tabs:
            # Select the tab corresponding to the server
            self.server_notebook.select(self.server_tabs[server_name])
        
        
    def start_server(self, server_name):
        """Start the selected server and begin monitoring it."""
        process = self.server_manager.start_server(server_name, lambda line: self.log_message(line, server_name))
        if process:  # Ensure the process object is returned
            self.log_message(f"Started {server_name} with PID: {process.pid}", server_name)

            def restart_if_needed():
                current_process = process  # Track the current process in this thread
                while True:
                    if current_process.poll() is not None:  # Process stopped
                        self.log_message(f"{server_name} has stopped.", server_name)
                        if self.restart_checkboxes[server_name].get():  # Check auto-restart flag
                            self.log_message(f"Restarting {server_name} due to crash...", server_name)
                            new_process = self.server_manager.start_server(server_name, lambda line: self.log_message(line, server_name))
                            current_process = new_process  # Update the process reference to the new one
                        else:
                            break
                    time.sleep(1)

            # Start the monitoring thread without passing `args` since restart_if_needed doesn't need it
            threading.Thread(target=restart_if_needed, daemon=True).start()
        else:
            self.log_message(f"Failed to start {server_name}.", server_name)



    def stop_server(self, server_name):
        """Stop the selected server and kill the process, only if it's running."""
        process = self.server_manager.processes.get(server_name)
    
        if process and process.poll() is None:  # Ensure the process is running before attempting to stop
            self.log_message(f"Stopping {server_name}...")
            process.terminate()  # Gracefully terminate the process
            process.wait()  # Wait for the process to fully terminate
            self.log_message(f"{server_name} has been stopped.")
        else:
            self.log_message(f"No running process found for {server_name}.")

    def save_server_log(self, server_name):
        """Save the server log to the selected log output directory."""
        if not self.log_output_dir:
            self.log_message("Please choose a log output directory.")
            return

        # Get the log content from the text widget
        log_content = self.server_text_logs[server_name].get("1.0", tk.END)

        # Create the log file name with the server name and timestamp
        log_filename = f"{server_name}_{self.get_timestamp()}.txt"

        # Build the full path
        log_filepath = os.path.join(self.log_output_dir, log_filename)

        try:
            # Save the log content to the file
            with open(log_filepath, 'w') as log_file:
                log_file.write(log_content)
            self.log_message(f"Log saved for {server_name} at {log_filepath}")
        except Exception as e:
            self.log_message(f"Failed to save log for {server_name}: {e}")

    

    def stop_world_server(self):
        """Stop only the World Server (xi_world.exe)."""
        self.server_manager.stop_server("World Server")

    def stop_search_server(self):
        """Stop only the Search Server (xi_search.exe)."""
        self.server_manager.stop_server("Search Server")

    def stop_map_server(self):
        """Stop only the Map Server (xi_map.exe)."""
        self.server_manager.stop_server("Map Server")

    def stop_connect_server(self):
        """Stop only the Connect Server (xi_connect.exe)."""
        self.server_manager.stop_server("Connect Server")


    def start_all_servers(self):
        """Start all servers at once."""
        for server_name in self.server_text_logs.keys():
            self.start_server(server_name)

    def stop_all_servers(self):
        """Stop all servers by calling their respective stop functions."""
        self.stop_world_server()
        self.stop_search_server()
        self.stop_map_server()
        self.stop_connect_server()

    def log_message(self, message, server_name=None):
        """Display log messages in the appropriate server's log window."""
        if server_name and server_name in self.server_text_logs:
            self.server_text_logs[server_name].insert(tk.END, message + '\n')
            self.server_text_logs[server_name].see(tk.END)

   

    def setup_sql_tab(self):
        # Create frame for SQL connection inputs
        connection_frame = tk.Frame(self.sql_tab, bg='#1e1e1e')
        connection_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        # Add input fields for SQL connection (host, user, password, database)
        tk.Label(connection_frame, text="Host:", fg="white", bg='#1e1e1e').grid(row=0, column=0, padx=5, pady=5)
        self.sql_host_entry = tk.Entry(connection_frame)
        self.sql_host_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(connection_frame, text="Username:", fg="white", bg='#1e1e1e').grid(row=1, column=0, padx=5, pady=5)
        self.sql_user_entry = tk.Entry(connection_frame)
        self.sql_user_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(connection_frame, text="Password:", fg="white", bg='#1e1e1e').grid(row=2, column=0, padx=5, pady=5)
        self.sql_password_entry = tk.Entry(connection_frame, show="*")
        self.sql_password_entry.grid(row=2, column=1, padx=5, pady=5)

        tk.Label(connection_frame, text="Database:", fg="white", bg='#1e1e1e').grid(row=3, column=0, padx=5, pady=5)
        self.sql_database_entry = tk.Entry(connection_frame)
        self.sql_database_entry.grid(row=3, column=1, padx=5, pady=5)

        tk.Label(connection_frame, text="Port:", fg="white", bg='#1e1e1e').grid(row=4, column=0, padx=5, pady=5)
        self.sql_port_entry = tk.Entry(connection_frame)
        self.sql_port_entry.grid(row=4, column=1, padx=5, pady=5)

        # Load saved config and populate the fields
        self.sql_host_entry.insert(0, self.config_handler.sql_host)
        self.sql_user_entry.insert(0, self.config_handler.sql_user)
        self.sql_database_entry.insert(0, self.config_handler.sql_database)
        self.sql_port_entry.insert(0, self.config_handler.sql_port)

        # Button to connect to the database
        self.connect_sql_button = tk.Button(connection_frame, text="Connect", command=self.connect_sql, bg='#28a745', fg='#ffffff')
        self.connect_sql_button.grid(row=5, column=1, pady=10)

        # Large text box for writing SQL queries
        self.query_text = ScrolledText(self.sql_tab, height=10, width=100, bg='#2e2e2e', fg='#ffffff', insertbackground='#ffffff')
        self.query_text.pack(pady=10, padx=10)

        # Button to execute the query
        self.execute_query_button = tk.Button(self.sql_tab, text="Execute Query", command=self.execute_query, bg='#28a745', fg='#ffffff')
        self.execute_query_button.pack(pady=5)

        # Text box to display the query result
        self.result_text = ScrolledText(self.sql_tab, height=10, width=100, bg='#2e2e2e', fg='#ffffff', insertbackground='#ffffff')
        self.result_text.pack(pady=10, padx=10)

         # Add a new tab for Errors/Logs
        self.error_log_tab = tk.Frame(self.notebook, bg='#1e1e1e')
        self.notebook.add(self.error_log_tab, text='Errors/Logs')
        # Text box for errors/logs in the new tab
        self.error_log_text = ScrolledText(self.error_log_tab, height=10, width=100, bg='#2e2e2e', fg='#ff5555', insertbackground='#ffffff')
        self.error_log_text.pack(pady=10, padx=10)

        # Add the connection status icon label at the bottom of the SQL tab
        self.sql_status_label = tk.Label(self.sql_tab, text="Connection Status: ", bg='#1e1e1e', fg='#ffffff')
        self.sql_status_label.pack(side=tk.LEFT, padx=10, pady=10)

        # Display the initial status as disconnected (use the first frame of the disconnected GIF)
        self.sql_status_icon = tk.Label(self.sql_tab, image=self.disconnected_gif_frames[6], bg='#1e1e1e')
        self.sql_status_icon.pack(side=tk.LEFT, padx=5, pady=10)

        # Clear Query button to clear the query input text box
        self.clear_query_button = tk.Button(self.sql_tab, text="Clear Query", command=self.clear_query, bg='#ffcc00', fg='#000000')
        self.clear_query_button.pack(pady=5)

        # Disconnect button to disconnect from the database
        self.disconnect_sql_button = tk.Button(self.sql_tab, text="Disconnect", command=self.disconnect_sql, bg='#dc3545', fg='#ffffff')
        self.disconnect_sql_button.pack(pady=5)

    def log_to_textbox(self, message, is_error=False):
        """Log message to the appropriate text box (results or error_log)."""
        if is_error:
            # Log errors in the error log tab
            self.error_log_text.insert(tk.END, message + "\n")
            self.error_log_text.see(tk.END)  # Scroll to the end
        else:
            # Log regular results in the main result text box
            self.result_text.insert(tk.END, message + "\n")
            self.result_text.see(tk.END)  # Scroll to the end


    def clear_query(self):
        """Clear the SQL query text box and clear results."""
        self.query_text.delete("1.0", tk.END)
        self.sql_manager.log_to_textbox("Results cleared.")  # Log via SQLManager
    

    def disconnect_sql(self):
        """Disconnect from the SQL database."""
        try:
            if self.sql_manager.is_connected():
                self.sql_manager.close()  # Disconnect from the database
                self.log_message("Successfully disconnected from the SQL database.", "SQL")
                self.update_sql_status_icon(connected=False)  # Switch to disconnected GIF
            else:
                self.log_message("No active database connection to disconnect.", "SQL")
        except Exception as e:
            self.log_message(f"Error during disconnect: {e}", "SQL")

    def connect_sql(self):
        """Connect to the SQL database using the information from input fields."""
        # Get input from the connection fields
        host = self.sql_host_entry.get()
        user = self.sql_user_entry.get()
        password = self.sql_password_entry.get()
        database = self.sql_database_entry.get()
        port = int(self.sql_port_entry.get())

        # Attempt to connect to the database
        try:
            success = self.sql_manager.connect(host, user, password, database, port)
            if success:
                self.log_to_error_log("Successfully connected to the SQL database.")  # Only 1 argument
                self.update_sql_status_icon(connected=True)
                self.config_handler.set_sql_config(host, user, database, port)
            else:
                self.log_to_error_log("Failed to connect to the SQL database. Check your credentials.")  # Only 1 argument
                self.update_sql_status_icon(connected=False)
        except Exception as e:
            self.log_to_error_log(f"Error connecting to the SQL database: {e}")  # Only 1 argument
            self.update_sql_status_icon(connected=False)

    def log_to_error_log(self, message):
        """Log message to the Errors/Logs tab."""
        # Ensure the error_log_text widget exists and log messages to it
        self.error_log_text.insert(tk.END, message + "\n")
        self.error_log_text.see(tk.END)  # Scroll to the end

    
    def execute_query(self):
        """Trigger query execution from the SQLManager."""
        query = self.query_text.get("1.0", tk.END).strip()
        if query:
            # Clear previous results before displaying new ones
            self.result_text.delete("1.0", tk.END)
            self.sql_manager.execute_query(query)
        else:
            self.result_text.insert(tk.END, "Please enter a SQL query.\n")


    def check_connection_status(self):
        """Check if the database connection is active and update the status icon."""
        if self.sql_manager.is_connected():
            self.log_message("Database connection is active.", "SQL")
            self.update_sql_status_icon(connected=True)
        else:
            self.log_message("Database connection is not active.", "SQL")
            self.update_sql_status_icon(connected=False)

        # Schedule the next check in 1000 milliseconds (1 second)
        self.root.after(1000, self.check_connection_status)  


