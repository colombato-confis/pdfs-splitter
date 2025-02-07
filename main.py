import os
import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

# Carpeta donde se guardarán los fragmentos
UPLOAD_FOLDER = "temp"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Asegurar que la carpeta "temp" existe
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def dividir_pdf_por_palabra(archivo_pdf, palabra_clave, ajuste_superior=0, ajuste_inferior=0):
    doc = fitz.open(archivo_pdf)
    reader = PdfReader(archivo_pdf)

    if len(doc) < 1:
        return {"error": "El PDF está vacío."}

    fragmentos = []  # Lista de fragmentos generados

    for num_pagina in range(len(doc)):
        pagina = doc[num_pagina]
        bloques = pagina.search_for(palabra_clave)

        if not bloques:
            continue  # Si no encuentra la palabra clave, pasa a la siguiente página

        bloques = sorted(bloques, key=lambda r: r.y0)

        for i in range(len(bloques)):
            y0 = max(0, bloques[i].y0 + ajuste_superior)

            if i < len(bloques) - 1:
                y1 = min(pagina.rect.y1, bloques[i+1].y0 + ajuste_inferior)
            else:
                y1 = pagina.rect.y1

            writer = PdfWriter()
            nueva_pagina = reader.pages[num_pagina]
            nueva_pagina.mediabox.lower_left = (0, y0)
            nueva_pagina.mediabox.upper_left = (0, y1)

            writer.add_page(nueva_pagina)

            output_pdf = os.path.join(app.config["UPLOAD_FOLDER"], f"fragmento_p{num_pagina + 1}_{i+1}.pdf")
            with open(output_pdf, "wb") as f:
                writer.write(f)

            fragmentos.append(f"fragmento_p{num_pagina + 1}_{i+1}.pdf")  # Guardamos solo el nombre

    return fragmentos

@app.route('/')
def home():
    return "¡Servidor Flask funcionando! Usa /dividir_pdf para dividir archivos PDF o /download/<filename> para descargar fragmentos generados."

@app.route('/dividir_pdf', methods=['POST'])
def dividir_pdf_api():
    if 'file' not in request.files:
        return jsonify({"error": "No se envió ningún archivo PDF"}), 400

    file = request.files['file']
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], "temp.pdf")
    file.save(file_path)

    palabra_clave = request.form.get("palabra_clave", "Leg")
    ajuste_superior = int(request.form.get("ajuste_superior", 50))
    ajuste_inferior = int(request.form.get("ajuste_inferior", 60))

    fragmentos = dividir_pdf_por_palabra(file_path, palabra_clave, ajuste_superior, ajuste_inferior)

    if isinstance(fragmentos, dict) and "error" in fragmentos:
        return jsonify(fragmentos), 400

    return jsonify({"fragmentos": fragmentos})

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """ Permite descargar un fragmento desde la carpeta correcta """
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    print(f"🔍 Intentando descargar el archivo: {file_path}")  # Log para depuración

    if not os.path.isfile(file_path):
        print(f"❌ Archivo no encontrado: {filename}")  # Log si el archivo no existe
        return jsonify({"error": f"El archivo {filename} no existe."}), 404

    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
