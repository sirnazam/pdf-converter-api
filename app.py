from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import tempfile, os, subprocess

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
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = os.path.join(tmp, file.filename)
        file.save(pdf_path)
        subprocess.run([
            'libreoffice', '--headless',
            '--convert-to', 'docx',
            '--outdir', tmp, pdf_path
        ], check=True)
        docx_path = os.path.join(tmp, 
            os.path.splitext(file.filename)[0] + '.docx')
        return send_file(docx_path, as_attachment=True,
            download_name=file.filename.replace('.pdf', '.docx'))

if __name__ == '__main__':
    app.run()
