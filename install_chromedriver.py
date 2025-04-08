import os
import subprocess
import requests
import zipfile
import shutil

def install_matching_chromedriver():
    try:
        # Get Chrome version
        result = subprocess.run(['google-chrome', '--version'], stdout=subprocess.PIPE)
        chrome_version = result.stdout.decode('utf-8').strip().split()
        if len(chrome_version) >= 3:
            chrome_version = chrome_version[2].split('.')[0]  # Extract major version
            print(f"Detected Chrome version: {chrome_version}")
        else:
            print("Could not parse Chrome version, defaulting to 134")
            chrome_version = "134"
        
        # Download matching ChromeDriver
        url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{chrome_version}"
        response = requests.get(url)
        version = response.text.strip()
        print(f"Downloading ChromeDriver version: {version}")
        
        download_url = f"https://chromedriver.storage.googleapis.com/{version}/chromedriver_linux64.zip"
        response = requests.get(download_url)
        
        with open("/tmp/chromedriver.zip", "wb") as f:
            f.write(response.content)
        
        # Extract and install
        with zipfile.ZipFile("/tmp/chromedriver.zip", "r") as zip_ref:
            zip_ref.extractall("/tmp")
        
        # Make executable and move to path
        os.chmod("/tmp/chromedriver", 0o755)
        
        # Backup original if it exists
        if os.path.exists("/usr/bin/chromedriver"):
            backup_path = "/usr/bin/chromedriver.backup"
            shutil.move("/usr/bin/chromedriver", backup_path)
            print(f"Backed up existing ChromeDriver to {backup_path}")
        
        # Move new chromedriver to path
        shutil.move("/tmp/chromedriver", "/usr/bin/chromedriver")
        print("Successfully installed matching ChromeDriver")
        
        # Clean up
        if os.path.exists("/tmp/chromedriver.zip"):
            os.remove("/tmp/chromedriver.zip")
        
        return True
    except Exception as e:
        print(f"Error installing ChromeDriver: {str(e)}")
        return False

if __name__ == "__main__":
    install_matching_chromedriver()