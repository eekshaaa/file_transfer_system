from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import os
import uuid
import datetime
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max upload
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Generate a secure API key if not already set
# In production, set this as an environment variable on Render
API_KEY = os.environ.get('API_KEY', str(uuid.uuid4()))
print(f"API Key: {API_KEY}")

# Store file information in memory (will reset on server restart)
# In production, you might want to use a database
FILES = []

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>File Transfer System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        h1, h2 {
            color: #2c3e50;
        }
        .container {
            background: #f9f9f9;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f2f2f2;
        }
        .button {
            display: inline-block;
            background-color: #3498db;
            color: white;
            padding: 8px 16px;
            text-decoration: none;
            border-radius: 4px;
            border: none;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }
        .button:hover {
            background-color: #2980b9;
        }
        .delete {
            background-color: #e74c3c;
        }
        .delete:hover {
            background-color: #c0392b;
        }
        input[type="file"] {
            margin: 10px 0;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            width: 100%;
        }
        .info {
            background-color: #f1f8e9;
            padding: 10px;
            border-radius: 4px;
            margin-top: 20px;
        }
        code {
            background: #f5f5f5;
            padding: 3px 5px;
            border-radius: 3px;
            font-family: monospace;
        }
        .footer {
            margin-top: 30px;
            color: #7f8c8d;
            font-size: 0.9em;
            text-align: center;
        }
    </style>
</head>
<body>
    <h1>File Transfer System</h1>
    
    <div class="container">
        <h2>Upload File</h2>
        <form action="/upload-web" method="post" enctype="multipart/form-data">
            <input type="file" name="file" required>
            <input type="hidden" name="api_key" value="{{ api_key }}">
            <button type="submit" class="button">Upload File</button>
        </form>
        <p>Maximum upload size: 100MB</p>
    </div>
    
    <div class="container">
        <h2>Available Files</h2>
        {% if files %}
            <table>
                <tr>
                    <th>Filename</th>
                    <th>Size</th>
                    <th>Uploaded</th>
                    <th>Actions</th>
                </tr>
                {% for file in files %}
                <tr>
                    <td>{{ file.filename }}</td>
                    <td>{{ file.size_formatted }}</td>
                    <td>{{ file.timestamp }}</td>
                    <td>
                        <a href="/download/{{ file.id }}?api_key={{ api_key }}" class="button">Download</a>
                        <a href="/delete/{{ file.id }}?api_key={{ api_key }}" class="button delete">Delete</a>
                    </td>
                </tr>
                {% endfor %}
            </table>
        {% else %}
            <p>No files available.</p>
        {% endif %}
    </div>
    
    <div class="container info">
        <h2>API Information</h2>
        <p>For programmatic access, use the following details:</p>
        <p><strong>Base URL:</strong> <code>{{ base_url }}</code></p>
        <p><strong>API Key:</strong> <code>{{ api_key }}</code></p>
        
        <h3>API Endpoints:</h3>
        <ul>
            <li><code>POST /api/upload</code> - Upload a file (include file in request body)</li>
            <li><code>GET /api/files</code> - List all files</li>
            <li><code>GET /api/download/{file_id}</code> - Download a specific file</li>
            <li><code>DELETE /api/files/{file_id}</code> - Delete a specific file</li>
        </ul>
        <p>All API requests must include an <code>Authorization: Bearer {{api_key}}</code> header.</p>
    </div>
    
    <div class="footer">
        <p>File Transfer System | Running on Render.com</p>
    </div>
</body>
</html>
"""

# Helper function to get file info
def get_file_info(file_id):
    for file in FILES:
        if file['id'] == file_id:
            return file
    return None

# Helper function to format file size
def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.1f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.1f} GB"

# Home route - Web Interface
@app.route('/')
def index():
    # Calculate base URL for API documentation
    base_url = request.url_root.rstrip('/')
    
    # Add formatted size to each file
    for file in FILES:
        file['size_formatted'] = format_size(file['size_bytes'])
    
    return render_template_string(
        HTML_TEMPLATE, 
        api_key=API_KEY,
        files=FILES,
        base_url=base_url
    )

# API: Upload file
@app.route('/api/upload', methods=['POST'])
def api_upload():
    # Verify API key
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f'Bearer {API_KEY}':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Check if file is included
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    
    file = request.files['file']
    
    # Check if file was selected
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save and record the file
    filename = secure_filename(file.filename)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_FOLDER, file_id)
    
    file.save(file_path)
    
    # Store file metadata
    file_info = {
        'id': file_id,
        'filename': filename,
        'path': file_path,
        'size_bytes': os.path.getsize(file_path),
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    FILES.append(file_info)
    
    return jsonify({
        'message': 'File uploaded successfully',
        'file_id': file_id,
        'filename': filename,
        'size': file_info['size_bytes']
    })

# Web Interface: Upload file
@app.route('/upload-web', methods=['POST'])
def web_upload():
    # Verify API key
    api_key = request.form.get('api_key')
    if api_key != API_KEY:
        return "Unauthorized", 403
    
    # Check if file is included
    if 'file' not in request.files:
        return "No file part in the request", 400
    
    file = request.files['file']
    
    # Check if file was selected
    if file.filename == '':
        return "No file selected", 400
    
    # Save and record the file
    filename = secure_filename(file.filename)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_FOLDER, file_id)
    
    file.save(file_path)
    
    # Store file metadata
    file_info = {
        'id': file_id,
        'filename': filename,
        'path': file_path,
        'size_bytes': os.path.getsize(file_path),
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    FILES.append(file_info)
    
    return redirect(url_for('index'))

# API: List files
@app.route('/api/files', methods=['GET'])
def api_list_files():
    # Verify API key
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f'Bearer {API_KEY}':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Return file list
    return jsonify({
        'files': [{
            'id': f['id'],
            'filename': f['filename'],
            'size': f['size_bytes'],
            'timestamp': f['timestamp']
        } for f in FILES]
    })

# API: Download file
@app.route('/api/download/<file_id>', methods=['GET'])
def api_download_file(file_id):
    # Verify API key
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f'Bearer {API_KEY}':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get file info
    file_info = get_file_info(file_id)
    if not file_info:
        return jsonify({'error': 'File not found'}), 404
    
    # Return file
    try:
        with open(file_info['path'], 'rb') as f:
            return app.response_class(
                f.read(),
                mimetype='application/octet-stream',
                headers={
                    'Content-Disposition': f'attachment; filename={file_info["filename"]}'
                }
            )
    except Exception as e:
        return jsonify({'error': f'Error downloading file: {str(e)}'}), 500

# Web Interface: Download file
@app.route('/download/<file_id>', methods=['GET'])
def web_download_file(file_id):
    # Verify API key
    api_key = request.args.get('api_key')
    if api_key != API_KEY:
        return "Unauthorized", 403
    
    # Get file info
    file_info = get_file_info(file_id)
    if not file_info:
        return "File not found", 404
    
    # Return file
    try:
        with open(file_info['path'], 'rb') as f:
            return app.response_class(
                f.read(),
                mimetype='application/octet-stream', 
                headers={
                    'Content-Disposition': f'attachment; filename={file_info["filename"]}'
                }
            )
    except Exception as e:
        return f"Error downloading file: {str(e)}", 500

# API: Delete file
@app.route('/api/files/<file_id>', methods=['DELETE'])
def api_delete_file(file_id):
    # Verify API key
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f'Bearer {API_KEY}':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get file info
    file_info = get_file_info(file_id)
    if not file_info:
        return jsonify({'error': 'File not found'}), 404
    
    # Delete file
    try:
        os.remove(file_info['path'])
        # Remove from list
        global FILES
        FILES = [f for f in FILES if f['id'] != file_id]
        return jsonify({'message': 'File deleted successfully'})
    except Exception as e:
        return jsonify({'error': f'Error deleting file: {str(e)}'}), 500

# Web Interface: Delete file
@app.route('/delete/<file_id>', methods=['GET'])
def web_delete_file(file_id):
    # Verify API key
    api_key = request.args.get('api_key')
    if api_key != API_KEY:
        return "Unauthorized", 403
    
    # Get file info
    file_info = get_file_info(file_id)
    if not file_info:
        return "File not found", 404
    
    # Delete file
    try:
        os.remove(file_info['path'])
        # Remove from list
        global FILES
        FILES = [f for f in FILES if f['id'] != file_id]
        return redirect(url_for('index'))
    except Exception as e:
        return f"Error deleting file: {str(e)}", 500

if __name__ == '__main__':
    # In development
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
