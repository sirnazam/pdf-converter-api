from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import tempfile, os, subprocess, glob, shutil, io, uuid

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def index():
    return jsonify({'message': 'PDF Converter API is running'})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

# ─── WORD TO PDF ────────────────────────────────────────────
@app.route('/convert', methods=['POST'])
def word_to_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    tmp_dir = tempfile.mkdtemp()

    try:
        input_path = os.path.join(tmp_dir, file.filename)
        file.save(input_path)

        subprocess.run([
            'libreoffice', '--headless',
            '--convert-to', 'pdf',
            '--outdir', tmp_dir,
            input_path
        ], capture_output=True, timeout=60)

        matches = glob.glob(os.path.join(tmp_dir, '*.pdf'))
        if not matches:
            return jsonify({'error': 'Conversion failed'}), 500

        with open(matches[0], 'rb') as f:
            file_data = io.BytesIO(f.read())

        shutil.rmtree(tmp_dir, ignore_errors=True)
        file_data.seek(0)

        download_name = os.path.splitext(file.filename)[0] + '.pdf'
        return send_file(
            file_data,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/pdf'
        )
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return jsonify({'error': str(e)}), 500


# ─── PDF TO WORD ────────────────────────────────────────────
@app.route('/pdf-to-word', methods=['POST'])
def pdf_to_word():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    tmp_dir = tempfile.mkdtemp()

    try:
        input_path = os.path.join(tmp_dir, 'input.pdf')
        file.save(input_path)

        subprocess.run([
            'libreoffice', '--headless',
            '--convert-to', 'docx',
            '--outdir', tmp_dir,
            input_path
        ], capture_output=True, timeout=60)

        matches = glob.glob(os.path.join(tmp_dir, '*.docx'))
        if not matches:
            return jsonify({'error': 'Conversion failed'}), 500

        with open(matches[0], 'rb') as f:
            file_data = io.BytesIO(f.read())

        shutil.rmtree(tmp_dir, ignore_errors=True)
        file_data.seek(0)

        download_name = os.path.splitext(file.filename)[0] + '.docx'
        return send_file(
            file_data,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return jsonify({'error': str(e)}), 500


# ─── PDF TO JPG ─────────────────────────────────────────────
@app.route('/pdf-to-jpg', methods=['POST'])
def pdf_to_jpg():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    tmp_dir = tempfile.mkdtemp()

    try:
        input_path = os.path.join(tmp_dir, 'input.pdf')
        file.save(input_path)

        subprocess.run([
            'libreoffice', '--headless',
            '--convert-to', 'jpg',
            '--outdir', tmp_dir,
            input_path
        ], capture_output=True, timeout=60)

        matches = glob.glob(os.path.join(tmp_dir, '*.jpg'))
        if not matches:
            return jsonify({'error': 'Conversion failed'}), 500

        if len(matches) == 1:
            with open(matches[0], 'rb') as f:
                file_data = io.BytesIO(f.read())
            shutil.rmtree(tmp_dir, ignore_errors=True)
            file_data.seek(0)
            return send_file(
                file_data,
                as_attachment=True,
                download_name='page-1.jpg',
                mimetype='image/jpeg'
            )
        else:
            zip_path = os.path.join(tmp_dir, 'pages.zip')
            shutil.make_archive(
                os.path.join(tmp_dir, 'pages'), 'zip', tmp_dir,
            )
            with open(zip_path, 'rb') as f:
                file_data = io.BytesIO(f.read())
            shutil.rmtree(tmp_dir, ignore_errors=True)
            file_data.seek(0)
            return send_file(
                file_data,
                as_attachment=True,
                download_name='pages.zip',
                mimetype='application/zip'
            )
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run()