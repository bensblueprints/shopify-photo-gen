import os
import base64
import io
import json
import re
import time
import uuid
import zipfile
import requests
from datetime import datetime
from pathlib import Path
from PIL import Image

from flask import Flask, request, jsonify, render_template, send_file, after_this_request
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max upload
app.config['UPLOAD_FOLDER'] = Path('uploads')
app.config['GENERATED_FOLDER'] = Path('generated')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

# Create folders
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)
app.config['GENERATED_FOLDER'].mkdir(exist_ok=True)

XAI_API_KEY = os.environ.get('XAI_API_KEY')
XAI_BASE_URL = 'https://api.x.ai/v1'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def sanitize_filename(name):
    """Clean a string to be safe for filenames."""
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[-\s]+', '-', name)
    return name.strip('-').lower()[:60]


def generate_intelligent_filename(original_filename, prompt, index=0):
    """Generate a Shopify-friendly product photo filename."""
    timestamp = datetime.now().strftime('%Y%m%d')
    
    # Extract key style/theme words from prompt
    style_keywords = []
    prompt_lower = prompt.lower()
    
    # Common e-commerce/photo style keywords
    style_triggers = [
        'studio', 'lifestyle', 'white background', 'flat lay', 'mockup',
        'minimal', 'luxury', 'vintage', 'modern', 'clean', 'professional',
        'product', 'editorial', 'catalog', 'advertising', 'commercial',
        'gradient', 'neon', 'pastel', 'dark', 'bright', 'warm', 'cool',
        '3d', 'render', 'photorealistic', 'illustration', 'sketch'
    ]
    
    for trigger in style_triggers:
        if trigger in prompt_lower:
            style_keywords.append(trigger.replace(' ', '-'))
    
    # Get base product name from original file
    base_name = Path(original_filename).stem
    base_name = sanitize_filename(base_name)
    
    if not base_name or len(base_name) < 2:
        base_name = 'product'
    
    style_part = '-'.join(style_keywords[:3]) if style_keywords else 'styled'
    
    if index > 0:
        filename = f"{base_name}_{style_part}_{timestamp}_{index}.png"
    else:
        filename = f"{base_name}_{style_part}_{timestamp}.png"
    
    return filename


def image_to_base64(image_path):
    """Convert an image file to base64 data URI."""
    with open(image_path, 'rb') as f:
        data = f.read()
    
    ext = image_path.suffix.lower()
    mime = 'image/png'
    if ext in ['.jpg', '.jpeg']:
        mime = 'image/jpeg'
    elif ext == '.webp':
        mime = 'image/webp'
    elif ext == '.gif':
        mime = 'image/gif'
    
    b64 = base64.b64encode(data).decode('utf-8')
    return f"data:{mime};base64,{b64}"


def process_image_with_xai(image_path, prompt, aspect_ratio=None, resolution=None):
    """Send image to xAI image editing API and return the result URL."""
    if not XAI_API_KEY:
        raise ValueError("XAI_API_KEY not configured")
    
    image_b64 = image_to_base64(image_path)
    
    payload = {
        "model": "grok-imagine-image",
        "prompt": prompt,
        "image": {
            "url": image_b64,
            "type": "image_url"
        }
    }
    
    if aspect_ratio:
        payload["aspect_ratio"] = aspect_ratio
    if resolution:
        payload["resolution"] = resolution
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {XAI_API_KEY}"
    }
    
    response = requests.post(
        f"{XAI_BASE_URL}/images/edits",
        headers=headers,
        json=payload,
        timeout=120
    )
    
    if response.status_code != 200:
        raise Exception(f"xAI API error: {response.status_code} - {response.text}")
    
    data = response.json()
    
    # Handle different response formats
    if 'data' in data and len(data['data']) > 0:
        return data['data'][0].get('url') or data['data'][0].get('b64_json')
    elif 'url' in data:
        return data['url']
    elif 'image' in data:
        return data['image']
    else:
        raise Exception(f"Unexpected response format: {json.dumps(data)[:500]}")


def download_image(url_or_b64, output_path):
    """Download image from URL or decode base64 to file."""
    if url_or_b64.startswith('data:'):
        # base64 data URI
        header, encoded = url_or_b64.split(',', 1)
        data = base64.b64decode(encoded)
        with open(output_path, 'wb') as f:
            f.write(data)
    elif url_or_b64.startswith('http'):
        # URL
        response = requests.get(url_or_b64, timeout=60)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            f.write(response.content)
    else:
        # Raw base64
        data = base64.b64decode(url_or_b64)
        with open(output_path, 'wb') as f:
            f.write(data)


def create_zip_archive(files, zip_path):
    """Create a ZIP archive of the given files."""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            zf.write(file_path, arcname=file_path.name)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/process', methods=['POST'])
def process_images():
    """Handle batch image upload and processing."""
    if not XAI_API_KEY:
        return jsonify({"error": "XAI_API_KEY not configured on server"}), 500
    
    prompt = request.form.get('prompt', '').strip()
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400
    
    # Optional parameters
    aspect_ratio = request.form.get('aspect_ratio', 'auto')
    resolution = request.form.get('resolution', '')
    if resolution not in ['1k', '2k']:
        resolution = None
    
    files = request.files.getlist('images')
    if not files or all(f.filename == '' for f in files):
        return jsonify({"error": "No images uploaded"}), 400
    
    # Filter valid files
    valid_files = []
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            valid_files.append(file)
    
    if not valid_files:
        return jsonify({"error": "No valid image files found"}), 400
    
    job_id = str(uuid.uuid4())[:8]
    upload_dir = app.config['UPLOAD_FOLDER'] / job_id
    gen_dir = app.config['GENERATED_FOLDER'] / job_id
    upload_dir.mkdir(exist_ok=True)
    gen_dir.mkdir(exist_ok=True)
    
    results = []
    errors = []
    
    for idx, file in enumerate(valid_files):
        original_filename = secure_filename(file.filename)
        upload_path = upload_dir / original_filename
        file.save(upload_path)
        
        try:
            # Call xAI API
            result = process_image_with_xai(
                upload_path, 
                prompt, 
                aspect_ratio=aspect_ratio if aspect_ratio != 'auto' else None,
                resolution=resolution
            )
            
            # Generate intelligent filename
            new_filename = generate_intelligent_filename(
                original_filename, prompt, index=idx
            )
            output_path = gen_dir / new_filename
            
            # Download/save the generated image
            download_image(result, output_path)
            
            results.append({
                "original": original_filename,
                "generated": new_filename,
                "status": "success"
            })
            
        except Exception as e:
            errors.append({
                "original": original_filename,
                "error": str(e)
            })
    
    # Create ZIP if any succeeded
    zip_path = None
    if results:
        zip_path = gen_dir / f"shopify-product-photos_{job_id}.zip"
        generated_files = [gen_dir / r['generated'] for r in results]
        create_zip_archive(generated_files, zip_path)
    
    return jsonify({
        "job_id": job_id,
        "success": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors,
        "zip_available": bool(results),
        "zip_filename": zip_path.name if zip_path else None
    })


@app.route('/api/download/<job_id>')
def download_zip(job_id):
    """Download the generated ZIP file."""
    zip_files = list(app.config['GENERATED_FOLDER'].glob(f"{job_id}/*.zip"))
    if not zip_files:
        return jsonify({"error": "ZIP not found"}), 404
    
    zip_path = zip_files[0]
    
    @after_this_request
    def cleanup(response):
        # Optional: cleanup after download
        return response
    
    return send_file(
        zip_path,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f"shopify-product-photos_{job_id}.zip"
    )


@app.route('/api/download-single/<job_id>/<filename>')
def download_single(job_id, filename):
    """Download a single generated image."""
    file_path = app.config['GENERATED_FOLDER'] / job_id / secure_filename(filename)
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404
    
    return send_file(file_path, as_attachment=True)


@app.route('/api/preview/<job_id>')
def get_preview(job_id):
    """Get list of generated files for preview."""
    gen_dir = app.config['GENERATED_FOLDER'] / job_id
    if not gen_dir.exists():
        return jsonify({"files": []})
    
    files = []
    for f in sorted(gen_dir.glob('*.png')):
        if f.suffix == '.png':
            with open(f, 'rb') as img:
                b64 = base64.b64encode(img.read()).decode('utf-8')
            files.append({
                "filename": f.name,
                "base64": f"data:image/png;base64,{b64}"
            })
    
    return jsonify({"files": files})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
