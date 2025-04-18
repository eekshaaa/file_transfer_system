import requests
import os
import sys
import json
import time
import shlex

CONFIG_FILE = "filetransfer_config.json"

def load_config():
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
                return json.load(f)
        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
            os.remove(CONFIG_FILE)
            return load_config()

def upload_file(file_path, config):
    # Normalize path
    file_path = os.path.abspath(file_path.strip('"\''))

    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return False

    try:
        file_size = os.path.getsize(file_path)
        print(f"Uploading {file_path} ({file_size/1024:.1f} KB)...")

        url = f"{config['server_url']}/api/upload"
        headers = {"Authorization": f"Bearer {config['api_key']}"}

        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            start_time = time.time()
            response = requests.post(url, files=files, headers=headers)
            elapsed_time = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                print("Upload successful.")
                print(f"File ID: {result['file_id']}")
                print(f"Size: {result['size']/1024:.1f} KB")
                print(f"Transfer rate: {file_size/1024/elapsed_time:.1f} KB/s")
                return True
            else:
                print(f"Upload failed: {response.json().get('error', 'Unknown error')}")
                return False
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return False

def list_files(config):
    try:
        url = f"{config['server_url']}/api/files"
        headers = {"Authorization": f"Bearer {config['api_key']}"}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            files = response.json().get('files', [])
            if not files:
                print("No files on server.")
            else:
                print(f"{'ID':<36} | {'Filename':<30} | {'Size':<10} | {'Uploaded':<20}")
                print("-" * 100)
                for file in files:
                    print(f"{file['id']:<36} | {file['filename']:<30} | {file['size']/1024:.1f} KB | {file['timestamp']:<20}")
        else:
            print(f"List failed: {response.json().get('error', 'Unknown error')}")
    except Exception as e:
        print(f"Error listing files: {str(e)}")

def download_file(file_id, output_path, config):
    output_path = output_path.strip('"\'')

    try:
        url = f"{config['server_url']}/api/download/{file_id}"
        headers = {"Authorization": f"Bearer {config['api_key']}"}
        response = requests.get(url, headers=headers, stream=True)

        if response.status_code == 200:
            filename = None
            content_disposition = response.headers.get('content-disposition')
            if content_disposition and 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[1].strip('"\'')
            if output_path and os.path.isdir(output_path):
                file_path = os.path.join(output_path, filename or f"download_{file_id}")
            elif output_path:
                file_path = output_path
            else:
                file_path = filename or f"download_{file_id}"

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(8192):
                    f.write(chunk)

            print(f"File downloaded to {file_path}")
        else:
            print(f"Download failed: {response.text}")
    except Exception as e:
        print(f"Download error: {str(e)}")

def delete_file(file_id, config):
    try:
        url = f"{config['server_url']}/api/files/{file_id}"
        headers = {"Authorization": f"Bearer {config['api_key']}"}
        response = requests.delete(url, headers=headers)
        if response.status_code == 200:
            print("File deleted successfully.")
        else:
            print(f"Delete failed: {response.json().get('error', 'Unknown error')}")
    except Exception as e:
        print(f"Delete error: {str(e)}")

def update_config():
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
    return load_config()

def show_help():
    print("\nFile Transfer Client")
    print("=" * 50)
    print("Commands:")
    print("  upload <filepath>              - Upload a file to the server")
    print("  list                           - List all files on the server")
    print("  download <file_id> [filepath]  - Download a file from the server")
    print("  delete <file_id>               - Delete a file from the server")
    print("  web                            - Open server in web browser")
    print("  config                         - Update server URL and API key")
    print("  help                           - Show this help message")
    print("  exit                           - Exit the program")
    print("=" * 50)

def open_web_interface(config):
    import webbrowser
    webbrowser.open(config['server_url'])

def parse_command(command_line):
    try:
        return shlex.split(command_line)
    except ValueError as e:
        print(f"Parse error: {str(e)}")
        return []

def interactive_mode():
    config = load_config()
    print(f"\nConnected to: {config['server_url']}")
    print("Type 'help' for commands")

    while True:
        try:
            command = input("\n> ").strip()
            if not command:
                continue

            parts = parse_command(command)
            if not parts:
                continue

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
                print(f"Updated. Connected to: {config['server_url']}")
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
            print(f"Unexpected error: {str(e)}")

def main():
    if len(sys.argv) < 2:
        interactive_mode()
        return

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
        print("Invalid command. Use 'python client.py help' for guidance.")

if __name__ == "__main__":
    main()
