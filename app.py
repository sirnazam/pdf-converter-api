from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import tempfile, os, subprocess, glob, shutil
import io

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
    with open(output_path, 'rb') as f:
        file_data = io.BytesIO(f.read())
    shutil.rmtree(tmp_dir, ignore_errors=True)
    file_data.seek(0)
    return send_file(
        file_data,
        as_attachment=True,
        download_name=file.filename.replace('.pdf', '.docx'),
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

if __name__ == '__main__':
    app.run()
