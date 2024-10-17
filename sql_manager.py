import mysql.connector
import tkinter as tk

class SQLManager:
    def __init__(self, gui=None):
        self.connection = None
        self.gui = gui  # Pass the GUI instance to SQLManager to access the textbox

    def connect(self, host, user, password, database, port=3306):
        """Connect to the SQL database using the provided credentials."""
        try:
            if self.connection and self.connection.is_connected():
                self.log_to_textbox("Already connected to the database.")
                return True

            # Establish a new connection
            self.connection = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                port=port
            )
            self.log_to_textbox(f"Successfully connected to database '{database}' at {host}:{port}")
            return True
        except mysql.connector.Error as e:
            self.log_to_error_log(f"Error connecting to the SQL database: {e}")
            return False  

    def execute_query(self, query, params=None):
        """Execute any SQL query and display the results in the GUI."""
        if self.connection is None or not self.is_connected():
            self.log_to_textbox("No database connection or lost connection. Please connect first.", is_error=True)
            return None

        try:
            # Use a basic cursor
            cursor = self.connection.cursor()

            # Execute the query
            cursor.execute(query, params)

            # Fetch the results if there are any
            if cursor.with_rows:
                results = cursor.fetchall()
                self.log_to_textbox(f"Query executed successfully. Fetched {len(results)} rows.", is_error=False)

                # Insert the result of the query into the GUI
                for row in results:
                    self.log_to_textbox(str(row), is_error=False)  # Show each row in the text box

            return cursor
        except mysql.connector.Error as e:
            # More detailed error logging
            self.log_to_textbox(f"SQL query failed: {e}", is_error=True)
            return None
        finally:
            cursor.close()  # Ensure the cursor is closed after execution


    def clear_unread_results(self):
        """Clear any unread results in the connection."""
        try:
            cursor = self.connection.cursor()
            while self.connection.unread_result:
                cursor.fetchall()  # Fetch and discard unread results
            self.log_to_textbox("Cleared unread results.")
        except mysql.connector.Error as e:
            self.log_error_to_textbox(f"Error while clearing unread results: {e}")

    def log_to_textbox(self, message, is_error=False):
        """Log message to the appropriate text box (results or error_log)."""
        if self.gui:
            if is_error:
                # Log errors in the error log tab
                self.gui.error_log_text.insert(tk.END, message + "\n")
                self.gui.error_log_text.see(tk.END)  # Scroll to the end
            else:
                # Log regular results in the main result text box
                self.gui.result_text.insert(tk.END, message + "\n")
                self.gui.result_text.see(tk.END)  # Scroll to the end

    def log_to_error_log(self, message):
        """Log message to the Errors/Logs tab."""
        # Log messages directly to the error_log_text widget
        if hasattr(self, 'error_log_text'):
            self.error_log_text.insert(tk.END, message + "\n")
            self.error_log_text.see(tk.END)  # Scroll to the end
        else:
            print(f"Error: {message}")  # Fallback logging to the console if the widget is missing


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
                self.log_error_to_textbox(f"Error while closing the connection: {e}")

    def clear_query(self):
        """Clear the SQL query text box and any unread results."""
        if self.gui and hasattr(self.gui, 'query_text'):
            self.gui.query_text.delete("1.0", tk.END)  # Clear the input box

        # Clear unread results if there are any
        if self.connection and self.connection.unread_result:
            cursor = self.connection.cursor()
            cursor.fetchall()  # Fetch and discard any unread results
            self.log_to_textbox("Unread results cleared.", is_error=False)
        else:
            self.log_to_textbox("No unread results to clear.", is_error=False)

        self.log_to_textbox("Query input cleared.", is_error=False)
