import os
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



class GUI:
    def __init__(self, root, config_handler, server_manager, resource_monitor, sql_manager):
        self.root = root
        self.config_handler = config_handler
        self.server_manager = server_manager
        self.resource_monitor = resource_monitor
        self.sql_manager = sql_manager
        self.log_output_dir = None  # Directory for log output
        self.monitoring_threads = {}  # Keep track of monitoring threads for each server
        self.sql_manager.gui = self
        self.server_manager.gui = self

        self.root.title("FFXI Server Manager")

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

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """Handle cleanup on application exit."""
        # Stop all servers before exiting
        self.stop_all_servers()

        # Any other cleanup (e.g., saving settings, logs, etc.)
        self.log_message("Shutting down FFXI Server Manager...")

        # Destroy the main window (close the application)
        self.root.destroy()
    
    def load_sql_status_icons(self):
        """Load images used for connection status (static PNGs)."""
        try:
        # Load static PNGs instead of GIFs
            self.connected_icon = ImageTk.PhotoImage(Image.open("connected.png").resize((30, 30)))
            self.disconnected_icon = ImageTk.PhotoImage(Image.open("disconnected.png").resize((30, 30)))
        except Exception as e:
            logging.error(f"Error loading status icons: {e}")
            
    
    
    def animate_sql_status(self):
        """Animate the connection status icon using the GIF frames."""
        frame = self.gif_frames[self.gif_frame_index]
        self.sql_status_icon.config(image=frame)
    
        # Update the frame index
        self.gif_frame_index = (self.gif_frame_index + 1) % len(self.gif_frames)
    
        # Continue the animation after 100 milliseconds
        self.root.after(500, self.animate_sql_status)


    

    def clear_results(self):
        """Clear any unread results before executing a new query."""
        if self.connection and self.connection.unread_result:
           self.connection.get_rows()  # Fetch all remaining results to clear the unread state


    def load_icons(self):
        """Load images used for server buttons and actions."""
        self.world_icon = ImageTk.PhotoImage(Image.open("world_icon.png").resize((60, 60)))
        self.search_icon = ImageTk.PhotoImage(Image.open("search_icon.png").resize((60, 60)))
        self.map_icon = ImageTk.PhotoImage(Image.open("map_icon.png").resize((60, 60)))
        self.connect_icon = ImageTk.PhotoImage(Image.open("connect_icon.png").resize((60, 60)))
        self.start_icon = ImageTk.PhotoImage(Image.open("start_icon.png").resize((60, 60)))
        self.stop_icon = ImageTk.PhotoImage(Image.open("stop_icon.png").resize((60, 60)))

    def update_sql_status_icon(self, connected):
        """Update the connection status icon based on the connection state."""
        if connected:
            self.sql_status_icon.config(image=self.connected_icon)
        else:
            self.sql_status_icon.config(image=self.disconnected_icon)

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

        self.exit_icon = ImageTk.PhotoImage(Image.open("exit.png").resize((60, 60)))

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

    def add_auto_restart_and_directories(self):
        """Add restart checkboxes and directory selection buttons to the sidebar."""
        # Initialize BooleanVars for each server's checkbox if they aren't initialized already
        if not self.restart_checkboxes:
            self.restart_checkboxes = {
                "World Server": tk.BooleanVar(),
                "Search Server": tk.BooleanVar(),
                "Connect Server": tk.BooleanVar(),
                "Map Server": tk.BooleanVar(),
            }

        # Create the checkboxes for each server
        for server in self.restart_checkboxes:
            checkbox = tk.Checkbutton(
                self.sidebar, text=f"Auto-Restart {server}",
                variable=self.restart_checkboxes[server],
                bg='#555555', fg='black',
                onvalue=True, offvalue=False  # Ensure the correct value is set
            )

            checkbox.pack(pady=5, anchor="w")

        # Directory selection buttons
        self.server_dir_button = tk.Button(
            self.sidebar, text="Choose Server Directory",
            command=self.choose_server_directory, bg='#555555', fg='#ffffff'
        )
        self.server_dir_button.pack(pady=5)

        self.log_dir_button = tk.Button(
            self.sidebar, text="Choose Log Output Folder",
            command=self.choose_log_directory, bg='#555555', fg='#ffffff'
        )
        self.log_dir_button.pack(pady=5)

        # Start All and Stop All buttons
        self.start_all_button = tk.Button(self.sidebar, text="Start All Servers", command=self.start_all_servers, bg='#28a745', fg='#ffffff')
        self.start_all_button.pack(pady=10, fill=tk.X)

        self.stop_all_button = tk.Button(self.sidebar, text="Stop All Servers", command=self.stop_all_servers, bg='#dc3545', fg='#ffffff')
        self.stop_all_button.pack(pady=10, fill=tk.X)

    def choose_server_directory(self):
        """Prompt the user to select the server directory."""
        directory = filedialog.askdirectory()
        if directory:
            self.server_manager.set_server_dir(directory)
            self.log_message(f"Server directory set to: {directory}")

    def choose_log_directory(self):
        """Prompt the user to select the log output folder."""
        directory = filedialog.askdirectory()
        if directory and os.access(directory, os.W_OK):
            self.log_output_dir = directory
            self.server_manager.log_output_dir = directory
            self.log_message(f"Log output folder set to: {directory}")
        else:
            self.log_message("Invalid directory or write permission issue.")

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
                        break

            # Start a thread to monitor and restart the server if needed
            threading.Thread(target=restart_if_needed, daemon=True).start()
        else:
            self.log_message(f"Failed to start {server_name}.", server_name)


    def stop_server(self, server_name):
        """Stop the selected server and kill the process."""
        # Ensure log output directory is set before stopping
        if not self.log_output_dir:
            self.log_message("Please choose a log output directory before stopping the server.")
            return

        # Save the server log before stopping the server
        self.save_server_log(server_name)

        # Kill the server process using the updated method
        self.server_manager.stop_server(server_name)

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

        # Add the connection status icon label at the bottom of the SQL tab
        self.sql_status_label = tk.Label(self.sql_tab, text="Connection Status: ", bg='#1e1e1e', fg='#ffffff')
        self.sql_status_label.pack(side=tk.LEFT, padx=10, pady=10)

         # Display the initial status as disconnected
        self.sql_status_icon = tk.Label(self.sql_tab, image=self.disconnected_icon, bg='#1e1e1e')
        self.sql_status_icon.pack(side=tk.LEFT, padx=5, pady=10)

        # Clear Query button to clear the query input text box
        self.clear_query_button = tk.Button(self.sql_tab, text="Clear Query", command=self.clear_query, bg='#ffcc00', fg='#000000')
        self.clear_query_button.pack(pady=5)

        # Disconnect button to disconnect from the database
        self.disconnect_sql_button = tk.Button(self.sql_tab, text="Disconnect", command=self.disconnect_sql, bg='#dc3545', fg='#ffffff')
        self.disconnect_sql_button.pack(pady=5)
    def clear_query(self):
        """Clear the SQL query text box."""
        self.query_text.delete("1.0", tk.END)
        self.log_message("Query cleared.", "SQL")

    def disconnect_sql(self):
        """Disconnect from the SQL database."""
        try:
            if self.sql_manager.is_connected():
                self.sql_manager.disconnect()
                self.log_message("Successfully disconnected from the SQL database.", "SQL")
                self.update_sql_status_icon(connected=False)
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
                self.log_message("Successfully connected to the SQL database.", "SQL")
                self.update_sql_status_icon(connected=True)
                self.config_handler.set_sql_config(host, user, database, port)
            else:
                self.log_message("Failed to connect to the SQL database. Check your credentials.", "SQL")
                self.update_sql_status_icon(connected=False)
        except Exception as e:
            self.log_message(f"Error connecting to the SQL database: {e}", "SQL")
            self.update_sql_status_icon(connected=False)

    
    def execute_query(self):
        """Trigger query execution from the SQLManager."""
        query = self.query_text.get("1.0", tk.END).strip()  # Get the query from input (assuming there's an input box)
        if query:
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


