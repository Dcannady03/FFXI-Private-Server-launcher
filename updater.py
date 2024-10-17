import os
import sys
import requests
import zipfile
import json
import tkinter.messagebox as messagebox

GITHUB_REPO = "Dcannady03/FFXI-Private-Server-launcher"  # Your GitHub repository
VERSION_FILE = "assets/config/version.json"  # Version file

def get_local_version():
    """Retrieve the current version of the application."""
    try:
        with open(VERSION_FILE, "r") as file:
            data = json.load(file)
            return data.get("version")
    except FileNotFoundError:
        return None

def check_for_updates():
    """Check the GitHub repository for the latest version."""
    repo_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    try:
        response = requests.get(repo_url)
        if response.status_code == 200:
            latest_release = response.json()
            latest_version = latest_release["tag_name"]
            return latest_version
        else:
            return None
    except requests.RequestException:
        return None

def is_newer_version(latest_version, current_version):
    """Compare version strings and return True if the latest version is newer."""
    # Strip any non-numeric prefix like 'v' from the version strings
    latest_version = latest_version.lstrip('v')  # Remove leading 'v' or other chars
    current_version = current_version.lstrip('v')

    latest_version_parts = [int(v) for v in latest_version.split('.')]
    current_version_parts = [int(v) for v in current_version.split('.')]

    return latest_version_parts > current_version_parts

def download_latest_release(latest_version, download_dir='updates'):
    """Download the latest release from GitHub as a zip file."""
    repo_url = f"https://github.com/{GITHUB_REPO}/releases/download/{latest_version}/FFXI-Server-Manager.zip"
    os.makedirs(download_dir, exist_ok=True)

    try:
        response = requests.get(repo_url, stream=True)
        zip_path = os.path.join(download_dir, f"FFXI-Server-Manager-{latest_version}.zip")

        with open(zip_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=128):
                file.write(chunk)
        return zip_path
    except requests.RequestException as e:
        raise Exception(f"Failed to download update: {e}")

def extract_update(zip_path, extract_to='.'):
    """Extract the downloaded zip file to the specified directory."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        return True
    except Exception as e:
        raise Exception(f"Failed to extract update: {e}")

def download_and_install_update(latest_version):
    """Download, extract, and install the update."""
    try:
        # Download the latest version as a zip file
        zip_path = download_latest_release(latest_version)
        print(f"Downloaded update to {zip_path}. Extracting...")

        # Extract the zip file to the application directory
        success = extract_update(zip_path)
        if success:
            print(f"Update to version {latest_version} was successful.")

            # Update the local version file
            with open(VERSION_FILE, 'w') as f:
                json.dump({"version": latest_version}, f)

            # Restart the application after update
            os.execv(sys.executable, ['python'] + sys.argv)
        else:
            print("Failed to extract the update.")
    except Exception as e:
        print(f"Error during update: {e}")
        raise

def check_and_update():
    """Check for updates and download the latest version if available."""
    local_version = get_local_version()
    latest_version = check_for_updates()

    if local_version is None:
        print("Local version not found.")
        messagebox.showerror("Update Error", "Local version not found.")
        return

    if latest_version and is_newer_version(latest_version, local_version):
        print(f"New version available: {latest_version}. Downloading update...")
        zip_path = download_latest_release(latest_version)
        extract_update(zip_path)
        print(f"Updated to version {latest_version}.")

        # Update the local version file
        with open(VERSION_FILE, 'w') as f:
            json.dump({"version": latest_version}, f)

        # Restart the application
        os.execv(sys.executable, ['python'] + sys.argv)
    else:
        print("You're already on the latest version.")
        # Show a messagebox to notify the user
        messagebox.showinfo("Update Status", "You're already on the latest version.")

# GUI integration to call the update check
def check_for_updates_gui(self):
    """Check for updates by calling the updater in the GUI."""
    try:
        check_and_update()  # This handles the entire update process, including restarting the app
        messagebox.showinfo("Update", "Update process completed. The application will restart.")
    except Exception as e:
        self.log_message(f"Error checking for updates: {e}")
        messagebox.showerror("Error", f"Error during update process: {e}")
