# Usa una imagen base de Python (en este caso, versión 3.10-slim)
FROM python:3.10-slim

# Actualiza el sistema e instala las dependencias necesarias:
# - poppler-utils: para la conversión de PDF a imágenes.
# - libzbar0: para que pyzbar funcione correctamente.
RUN apt-get update && \
    apt-get install -y poppler-utils libzbar0 && \
    rm -rf /var/lib/apt/lists/*

# Define el directorio de trabajo en el contenedor
WORKDIR /app

# Copia el archivo de requerimientos y luego instala las dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código del proyecto al directorio de trabajo
COPY . .

# Define el comando de entrada para el contenedor.
# Nota: El script espera recibir la ruta de un PDF como argumento.
ENTRYPOINT ["python", "script.py"]
