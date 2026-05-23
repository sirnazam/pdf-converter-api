from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import tempfile, os, subprocess, glob, shutil

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def index():
    return jsonify({'message': 'PDF Converter API is running'})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/convert', methods=['POST'])
def convert_docx():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    with tempfile.TemporaryDirectory() as tmp:
        docx_path = os.path.join(tmp, file.filename)
        file.save(docx_path)
        subprocess.run([
            'libreoffice', '--headless',
            '--convert-to', 'pdf',
            '--outdir', tmp, docx_path
        ], check=True)
        pdf_path = os.path.join(tmp, os.path.splitext(file.filename)[0] + '.pdf')
        return send_file(pdf_path, as_attachment=True,
                        download_name=file.filename.replace('.docx', '.pdf'))

@app.route('/pdf-to-word', methods=['POST'])
def pdf_to_word():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    tmp_dir = tempfile.mkdtemp()
    try:
        input_path = os.path.join(tmp_dir, 'input.pdf')
        file.save(input_path)
        result = subprocess.run([
            'libreoffice', '--headless', '--convert-to', 'docx',
            '--outdir', tmp_dir, input_path
        ], capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return jsonify({'error': 'Conversion failed', 'details': result.stderr}), 500

        matches = glob.glob(os.path.join(tmp_dir, '*.docx'))
        if not matches:
            return jsonify({'error': 'Conversion failed', 'details': 'No output file found'}), 500

        output_path = matches[0]
        return send_file(output_path, as_attachment=True,
            download_name=file.filename.replace('.pdf', '.docx'))
    finally:
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass

if __name__ == '__main__':
    app.run()
