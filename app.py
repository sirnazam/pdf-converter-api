from flask import Flask, request, send_file
import tempfile, os, subprocess

app = Flask(__name__)

@app.route('/convert', methods=['POST'])
def convert_docx():
    file = request.files['file']
    with tempfile.TemporaryDirectory() as tmp:
        docx_path = os.path.join(tmp, file.filename)
        file.save(docx_path)
        # Use LibreOffice to convert DOCX to PDF in headless mode
        subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', tmp,
            docx_path
        ], check=True)
        pdf_path = os.path.join(tmp, os.path.splitext(file.filename)[0] + '.pdf')
        return send_file(pdf_path, as_attachment=True)

if __name__ == '__main__':
    app.run()
