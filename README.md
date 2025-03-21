## 1. Construir la Imagen Docker

Abre una terminal en la carpeta raíz del proyecto y ejecuta el siguiente comando para construir la imagen:

```bash
docker build -t auto_doc_processor .
```

> **Nota:**  
> El flag `-t auto_doc_processor` etiqueta la imagen con ese nombre.

---

## 2. Ejecutar el Contenedor

Para ejecutar el contenedor y procesar un PDF, monta el directorio donde se encuentre el archivo PDF en el contenedor y pásale la ruta del PDF como argumento. Por ejemplo, si tienes un PDF en `/home/usuario/pdf/ejemplo.pdf`, puedes ejecutar:

```bash
docker run --rm -v /home/usuario/pdf:/data auto_doc_processor /data/ejemplo.pdf
```

> **Detalles del comando:**  
> - `--rm` hace que el contenedor se elimine automáticamente al finalizar.  
> - `-v /home/usuario/pdf:/data` monta el directorio local `/home/usuario/pdf` en el directorio `/data` del contenedor.  
> - `/data/ejemplo.pdf` es la ruta del PDF dentro del contenedor que se pasa como argumento al script.
