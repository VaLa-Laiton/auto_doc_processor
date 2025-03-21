import sys
import os
import io
import PyPDF2
from pdf2image import convert_from_path
from PIL import Image
from pyzbar.pyzbar import decode

# ================================
# CONFIGURACIÓN DEL SCRIPT
# ================================
BASE_NAME = "XXX-NOV-2024-"
starting_serial = 131
SERIAL_WIDTH = 5
DPI = 200

# Configuración para Linux: se asume que poppler-utils está instalado y en el PATH
POPPLER_PATH = None

# ================================
# FUNCIONES
# ================================

def decode_qr_from_image(image: Image.Image) -> str:
    """
    Recibe una imagen (PIL) y recorta el cuadrante superior derecho,
    donde se asume se encuentra el código QR. Luego, decodifica y devuelve
    el texto contenido en el QR. Si no encuentra QR, retorna cadena vacía.
    """
    width, height = image.size
    # Se asume que el QR está en el cuadrante superior derecho.
    crop_box = (width // 2, 0, width, height // 2)
    cropped = image.crop(crop_box)
    codes = decode(cropped)
    if codes:
        try:
            data = codes[0].data.decode("utf-8")
        except Exception:
            data = codes[0].data
        qr_text = data.strip()
        print(f"[DEBUG] QR detectado: {qr_text}")
        return qr_text
    else:
        print("[DEBUG] No se detectó QR en la imagen")
    return ""

def process_pdf(pdf_path: str):
    """
    Recorre el PDF y clasifica las páginas en función del QR.
    Se carga el contenido completo en memoria para evitar que el archivo se cierre.
    """
    print(f"[DEBUG] Abriendo PDF: {pdf_path}")
    # Cargar el PDF completo en memoria usando BytesIO
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    pdf_stream = io.BytesIO(pdf_bytes)
    pdf_reader = PyPDF2.PdfReader(pdf_stream)
    total_pages = len(pdf_reader.pages)
    print(f"[DEBUG] Total de páginas en el PDF: {total_pages}")

    print("[DEBUG] Convirtiendo páginas a imágenes...")
    # Convertir usando la ruta de poppler si está definida, sino se usa el PATH
    if POPPLER_PATH:
        pages_images = convert_from_path(pdf_path, dpi=DPI, poppler_path=POPPLER_PATH)
    else:
        pages_images = convert_from_path(pdf_path, dpi=DPI)
    print(f"[DEBUG] Conversión completada. Total de imágenes obtenidas: {len(pages_images)}")

    documents = []         # Cada elemento: (tipo_doc, [índices de páginas])
    current_doc_pages = [] # Páginas acumuladas del documento actual

    for i in range(total_pages):
        print(f"[DEBUG] Procesando página {i+1} de {total_pages}")
        image = pages_images[i]
        qr_text = decode_qr_from_image(image)
        if qr_text == "Separador":
            print(f"[DEBUG] Página {i+1} es un Separador")
            if current_doc_pages:
                documents.append(("document", current_doc_pages))
                print(f"[DEBUG] Documento finalizado con páginas: {current_doc_pages}")
                current_doc_pages = []
        elif qr_text == "No Disponible":
            print(f"[DEBUG] Página {i+1} es No Disponible")
            if current_doc_pages:
                documents.append(("document", current_doc_pages))
                print(f"[DEBUG] Documento finalizado con páginas: {current_doc_pages}")
                current_doc_pages = []
            documents.append(("no_disponible", [i]))
        else:
            print(f"[DEBUG] Página {i+1} agregada al documento actual")
            current_doc_pages.append(i)

    if current_doc_pages:
        documents.append(("document", current_doc_pages))
        print(f"[DEBUG] Documento finalizado con páginas: {current_doc_pages}")

    print(f"[DEBUG] Proceso de clasificación completado. Documentos encontrados: {len(documents)}")
    return documents, pdf_reader

def extract_documents(pdf_path: str, base_name: str, starting_serial: int):
    """
    Extrae cada documento (segmento de páginas) del PDF original y lo guarda
    como un archivo PDF separado. El nombre del archivo se forma usando el
    'base_name' y un número de serie que se incrementa para cada documento.
    Los documentos extraídos se guardan en una carpeta "documentos_extraidos"
    en el mismo directorio del PDF original.
    """
    print("[DEBUG] Iniciando extracción de documentos")
    documents, pdf_reader = process_pdf(pdf_path)
    output_dir = os.path.join(os.path.dirname(pdf_path), "documentos_extraidos")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"[DEBUG] Directorio creado: {output_dir}")
    else:
        print(f"[DEBUG] Directorio existente: {output_dir}")

    current_serial = starting_serial
    for doc in documents:
        doc_type, page_indices = doc
        print(f"[DEBUG] Extrayendo documento tipo '{doc_type}' con páginas: {page_indices}")
        pdf_writer = PyPDF2.PdfWriter()
        for idx in page_indices:
            pdf_writer.add_page(pdf_reader.pages[idx])
        file_name = f"{base_name}{str(current_serial).zfill(SERIAL_WIDTH)}.pdf"
        file_path = os.path.join(output_dir, file_name)
        with open(file_path, "wb") as out_file:
            pdf_writer.write(out_file)
        print(f"Documento extraído: {file_path} (páginas: {page_indices})")
        current_serial += 1

# ================================
# BLOQUE PRINCIPAL
# ================================

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python script.py ruta_del_pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    print("[DEBUG] Iniciando el proceso de extracción con el PDF:", pdf_path)
    extract_documents(pdf_path, BASE_NAME, starting_serial)
    print("[DEBUG] Proceso completado.")
