import sys
import os
import io
import time                     # Para medir el tiempo de ejecución
import concurrent.futures       # Para procesamiento paralelo
import PyPDF2
from pdf2image import convert_from_path
from PIL import Image
from pyzbar.pyzbar import decode

# ================================
# CONFIGURACIÓN DEL SCRIPT
# ================================
BASE_NAME = "XXX-NOV-2024-"      # Prefijo base para los nombres de los PDFs extraídos
starting_serial = 131            # Número de serie inicial
SERIAL_WIDTH = 5                 # Ancho fijo para el número de serie (ej. 00131)
DPI = 200                        # Resolución para la conversión de páginas a imágenes

# En Linux se asume que poppler-utils está instalado y accesible desde el PATH
POPPLER_PATH = None

# Control de depuración: cambiar a False para optimización (se reduce la E/S)
DEBUG = False

def debug_print(message: str):
    if DEBUG:
        print(message)

# ================================
# FUNCIONES
# ================================

def decode_qr_from_image(image: Image.Image) -> str:
    """
    Recibe una imagen (PIL) y extrae la región del cuadrante superior derecho,
    la convierte a escala de grises y decodifica el código QR.
    Retorna el texto contenido en el QR o una cadena vacía si no se detecta.
    """
    width, height = image.size
    # Define la región del cuadrante superior derecho
    crop_box = (width // 2, 0, width, height // 2)
    # Recorta y convierte la imagen a escala de grises para acelerar el procesamiento
    cropped = image.crop(crop_box).convert("L")
    codes = decode(cropped)
    if codes:
        try:
            data = codes[0].data.decode("utf-8")
        except Exception:
            data = codes[0].data
        qr_text = data.strip()
        debug_print(f"[DEBUG] QR detectado: {qr_text}")
        return qr_text
    else:
        debug_print("[DEBUG] No se detectó QR en la imagen")
    return ""

def process_pdf(pdf_path: str):
    """
    Procesa el PDF:
      - Lee el PDF completo en memoria.
      - Convierte cada página a imagen usando múltiples hilos.
      - Decodifica los códigos QR en cada imagen de forma concurrente.
      - Clasifica las páginas según el contenido del QR.
    
    Retorna una tupla:
      (lista de documentos clasificados, objeto PdfReader)
    """
    debug_print(f"[DEBUG] Abriendo PDF: {pdf_path}")
    # Lee el PDF completo en memoria
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    pdf_stream = io.BytesIO(pdf_bytes)
    pdf_reader = PyPDF2.PdfReader(pdf_stream)
    total_pages = len(pdf_reader.pages)
    debug_print(f"[DEBUG] Total de páginas en el PDF: {total_pages}")

    # Define el número de hilos a utilizar basado en la cantidad de núcleos disponibles
    thread_count = os.cpu_count() or 1

    debug_print("[DEBUG] Convirtiendo páginas a imágenes...")
    # Convierte las páginas a imágenes usando thread_count
    if POPPLER_PATH:
        pages_images = convert_from_path(pdf_path, dpi=DPI, thread_count=thread_count, poppler_path=POPPLER_PATH)
    else:
        pages_images = convert_from_path(pdf_path, dpi=DPI, thread_count=thread_count)
    debug_print(f"[DEBUG] Conversión completada. Total de imágenes obtenidas: {len(pages_images)}")

    # Decodificación del QR en cada página:
    # Si DEBUG está desactivado, se procesa en paralelo para mayor velocidad.
    if not DEBUG:
        with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
            qr_texts = list(executor.map(decode_qr_from_image, pages_images))
    else:
        qr_texts = []
        for i, image in enumerate(pages_images):
            debug_print(f"[DEBUG] Procesando página {i+1} de {total_pages}")
            qr_texts.append(decode_qr_from_image(image))

    # Clasifica las páginas en documentos según el QR detectado
    documents = []
    current_doc_pages = []
    for i, qr_text in enumerate(qr_texts):
        if qr_text == "Separador":
            debug_print(f"[DEBUG] Página {i+1} es un Separador")
            if current_doc_pages:
                documents.append(("document", current_doc_pages))
                debug_print(f"[DEBUG] Documento finalizado con páginas: {current_doc_pages}")
                current_doc_pages = []
        elif qr_text == "No Disponible":
            debug_print(f"[DEBUG] Página {i+1} es No Disponible")
            if current_doc_pages:
                documents.append(("document", current_doc_pages))
                debug_print(f"[DEBUG] Documento finalizado con páginas: {current_doc_pages}")
                current_doc_pages = []
            documents.append(("no_disponible", [i]))
        else:
            debug_print(f"[DEBUG] Página {i+1} agregada al documento actual")
            current_doc_pages.append(i)
    if current_doc_pages:
        documents.append(("document", current_doc_pages))
        debug_print(f"[DEBUG] Documento finalizado con páginas: {current_doc_pages}")
    debug_print(f"[DEBUG] Proceso de clasificación completado. Documentos encontrados: {len(documents)}")
    return documents, pdf_reader

def extract_documents(pdf_path: str, base_name: str, starting_serial: int):
    """
    Extrae y guarda en archivos PDF separados cada uno de los documentos identificados
    en el PDF original. Cada documento se nombra utilizando un prefijo y un número de serie.
    Los archivos se guardan en la carpeta "documentos_extraidos", en el mismo directorio
    que el PDF original.
    """
    debug_print("[DEBUG] Iniciando extracción de documentos")
    documents, pdf_reader = process_pdf(pdf_path)
    # Define el directorio de salida para los documentos extraídos
    output_dir = os.path.join(os.path.dirname(pdf_path), "documentos_extraidos")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        debug_print(f"[DEBUG] Directorio creado: {output_dir}")
    else:
        debug_print(f"[DEBUG] Directorio existente: {output_dir}")

    current_serial = starting_serial
    for doc in documents:
        doc_type, page_indices = doc
        debug_print(f"[DEBUG] Extrayendo documento tipo '{doc_type}' con páginas: {page_indices}")
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
    
    # Inicia el cronómetro
    start_time = time.time()
    
    # Extrae los documentos
    extract_documents(pdf_path, BASE_NAME, starting_serial)
    
    # Calcula el tiempo transcurrido
    elapsed_time = time.time() - start_time
    print("[DEBUG] Proceso completado.")
    
    # Muestra el tiempo de ejecución en estilo "cowsay"
    print(" _____________________________________________")
    print(f"< Proceso completado en {elapsed_time:.2f} segundos >")
    print(" ---------------------------------------------")
    print("        \\   ^__^")
    print("         \\  (oo)\\_______")
    print("            (__)\\       )\\/\\")
    print("                ||----w |")
    print("                ||     ||")
