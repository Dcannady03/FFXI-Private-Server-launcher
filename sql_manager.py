import mysql.connector  # For MySQL
import logging
import tkinter as tk
class SQLManager:
    def __init__(self, gui=None):
        self.connection = None
        self.gui = gui  # Pass the GUI instance to SQLManager to access the textbox

    def connect(self, host, user, password, database, port=3306):
        """Connect to the MySQL database using the provided credentials."""
        try:
            if self.connection and self.connection.is_connected():
                self.log_to_textbox("Already connected to the database.")
                return True

            self.connection = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                port=port
            )
            self.log_to_textbox(f"Successfully connected to database '{database}' at {host}:{port}")
            return True
        except mysql.connector.Error as err:
            self.log_to_textbox(f"Error connecting to database: {err}")
            return False

    def execute_query(self, query, params=None):
        """Execute any SQL query and display the results in the GUI."""
        if self.connection is None or not self.is_connected():
            self.log_to_textbox("No database connection or lost connection. Please connect first.")
            return None

        try:
            if self.connection.unread_result:
                self.connection.get_rows()  # Fetch all remaining results to clear unread state

            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()

            if cursor.with_rows:
                results = cursor.fetchall()
                self.log_to_textbox(f"Query executed successfully. Fetched {len(results)} rows.")

                # Insert the result of the query into the GUI
                for row in results:
                    self.log_to_textbox(str(row))  # Show each row in the text box

            return cursor
        except mysql.connector.Error as e:
            self.log_to_textbox(f"SQL query failed: {e}")
            return None

    def log_to_textbox(self, message):
        """Log message to the GUI's result_text."""
        if self.gui:  # Only log if the GUI instance is available
            self.gui.result_text.insert(tk.END, message + "\n")
            self.gui.result_text.see(tk.END)  # Scroll to the end

    def is_connected(self):
        """Check if the connection to the database is still active."""
        if self.connection:
            return self.connection.is_connected()
        return False

    def close(self):
        """Close the connection."""
        if self.connection:
            try:
                self.connection.close()
                self.log_to_textbox("Database connection closed.")
            except mysql.connector.Error as e:
                self.log_to_textbox(f"Error while closing the connection: {e}")
