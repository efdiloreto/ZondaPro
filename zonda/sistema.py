from tempfile import NamedTemporaryFile


def guardar_archivo_temporal(contenido: str, sufijo: str):
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False, suffix=sufijo
    ) as tmp:
        tmp.write(contenido)
        return tmp.name
