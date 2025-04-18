import requests
import os
import sys
import json
import time

CONFIG_FILE = "filetransfer_config.json"

def load_config():
    """Load server URL and API key from config file or prompt user."""
    if not os.path.exists(CONFIG_FILE):
        print("First-time setup: Please enter your server details.")
        server_url = input("Enter the server URL (e.g., https://your-app.onrender.com): ")
        api_key = input("Enter the API key (from server): ")
        
        config = {
            "server_url": server_url.rstrip('/'),
            "api_key": api_key
        }
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        
        print(f"Configuration saved to {CONFIG_FILE}")
        return config
    else:
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
            os.remove(CONFIG_FILE)
            return load_config()

def upload_file(file_path, config):
    """Upload a file to the server."""
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return False

    try:
        # Get file size for progress reporting
        file_size = os.path.getsize(file_path)
        print(f"Uploading {file_path} ({file_size/1024:.1f} KB)...")
        
        # Prepare the request
        url = f"{config['server_url']}/api/upload"
        headers = {"Authorization": f"Bearer {config['api_key']}"}
        
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            
            # Upload with progress indicator
            start_time = time.time()
            response = requests.post(url, files=files, headers=headers)
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Success! File uploaded.")
                print(f"  File ID: {result['file_id']}")
                print(f"  Size: {result['size']/1024:.1f} KB")
                print(f"  Transfer rate: {file_size/1024/elapsed_time:.1f} KB/s")
                return True
            else:
                print(f"✗ Error: {response.json().get('error', 'Unknown error')}")
                print(f"  Status code: {response.status_code}")
                return False
    except Exception as e:
        print(f"✗ Error during upload: {str(e)}")
        return False

def list_files(config):
    """List files available on the server."""
    try:
        url = f"{config['server_url']}/api/files"
        headers = {"Authorization": f"Bearer {config['api_key']}"}
        
        print("Fetching file list from server...")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            files = response.json().get('files', [])
            if not files:
                print("No files found on server.")
            else:
                print("\nFiles on server:")
                print("-" * 80)
                print(f"{'ID':<36} | {'Filename':<30} | {'Size':<10} | {'Uploaded':<20}")
                print("-" * 80)
                for file in files:
                    size_formatted = f"{file['size']/1024:.1f} KB"
                    print(f"{file['id']:<36} | {file['filename']:<30} | {size_formatted:<10} | {file['timestamp']:<20}")
        else:
            print(f"Error: {response.json().get('error', 'Unknown error')}")
    except Exception as e:
        print(f"Error listing files: {str(e)}")

def download_file(file_id, output_path, config):
    """Download a file from the server."""
    try:
        url = f"{config['server_url']}/api/download/{file_id}"
        headers = {"Authorization": f"Bearer {config['api_key']}"}
        
        print(f"Downloading file with ID: {file_id}...")
        start_time = time.time()
        response = requests.get(url, headers=headers, stream=True)
        
        if response.status_code == 200:
            # Extract the filename from content-disposition header
            filename = None
            content_disposition = response.headers.get('content-disposition')
            if content_disposition and 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[1].strip('"\'')
            
            # If output_path is a directory, use the original filename
            if os.path.isdir(output_path):
                if not filename:
                    filename = f"download_{file_id}"
                file_path = os.path.join(output_path, filename)
            else:
                file_path = output_path
            
            # Save the file with progress indicator
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Print progress
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\rDownloading: {percent:.1f}% ({downloaded/1024:.1f} KB / {total_size/1024:.1f} KB)", end="")
            
            elapsed_time = time.time() - start_time
            print(f"\n✓ File downloaded successfully to {file_path}")
            if elapsed_time > 0:
                print(f"  Transfer rate: {total_size/1024/elapsed_time:.1f} KB/s")
        else:
            print(f"✗ Error: {response.text}")
    except Exception as e:
        print(f"✗ Error downloading file: {str(e)}")

def delete_file(file_id, config):
    """Delete a file from the server."""
    try:
        url = f"{config['server_url']}/api/files/{file_id}"
        headers = {"Authorization": f"Bearer {config['api_key']}"}
        
        print(f"Deleting file with ID: {file_id}...")
        response = requests.delete(url, headers=headers)
        
        if response.status_code == 200:
            print(f"✓ File deleted successfully")
        else:
            print(f"✗ Error: {response.json().get('error', 'Unknown error')}")
    except Exception as e:
        print(f"✗ Error deleting file: {str(e)}")

def update_config():
    """Update the server URL and API key."""
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
    
    return load_config()

def show_help():
    """Display help information."""
    print("\nFile Transfer Client")
    print("=" * 50)
    print("Commands:")
    print("  upload <filepath>              - Upload a file to the server")
    print("  list                           - List all files on the server")
    print("  download <file_id> [filepath]  - Download a file from the server")
    print("  delete <file_id>               - Delete a file from the server")
    print("  web                            - Open server in web browser (if available)")
    print("  config                         - Update server URL and API key")
    print("  help                           - Show this help message")
    print("  exit                           - Exit the program")
    print("=" * 50)

def open_web_interface(config):
    """Try to open the web interface in a browser."""
    import webbrowser
    url = config['server_url']
    
    try:
        print(f"Opening {url} in your browser...")
        webbrowser.open(url)
    except Exception as e:
        print(f"Could not open browser: {str(e)}")
        print(f"Please manually visit: {url}")

def interactive_mode():
    """Run the client in interactive mode."""
    config = load_config()
    
    print("\nFile Transfer Client")
    print("=" * 50)
    print(f"Connected to: {config['server_url']}")
    print("Type 'help' for available commands")
    
    while True:
        try:
            command = input("\n> ").strip()
            
            if not command:
                continue
            
            parts = command.split()
            cmd = parts[0].lower()
            
            if cmd == "upload" and len(parts) >= 2:
                upload_file(parts[1], config)
            elif cmd == "list":
                list_files(config)
            elif cmd == "download" and len(parts) >= 2:
                output_path = parts[2] if len(parts) >= 3 else "."
                download_file(parts[1], output_path, config)
            elif cmd == "delete" and len(parts) >= 2:
                delete_file(parts[1], config)
            elif cmd == "web":
                open_web_interface(config)
            elif cmd == "config":
                config = update_config()
                print(f"Updated configuration. Connected to: {config['server_url']}")
            elif cmd == "help":
                show_help()
            elif cmd in ["exit", "quit"]:
                print("Exiting...")
                break
            else:
                print("Invalid command. Type 'help' for available commands.")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {str(e)}")

def main():
    """Main function to handle command line arguments or start interactive mode."""
    if len(sys.argv) < 2:
        # No arguments, start interactive mode
        interactive_mode()
        return
    
    # Process command line arguments
    config = load_config()
    command = sys.argv[1].lower()
    
    if command == "upload" and len(sys.argv) >= 3:
        upload_file(sys.argv[2], config)
    elif command == "list":
        list_files(config)
    elif command == "download" and len(sys.argv) >= 3:
        output_path = sys.argv[3] if len(sys.argv) >= 4 else "."
        download_file(sys.argv[2], output_path, config)
    elif command == "delete" and len(sys.argv) >= 3:
        delete_file(sys.argv[2], config)
    elif command == "web":
        open_web_interface(config)
    elif command == "config":
        update_config()
    elif command == "help":
        show_help()
    else:
        print("Invalid command. Type 'python client.py help' for available commands.")

if __name__ == "__main__":
    main()
