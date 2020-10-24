# Distribuir

## Importante

Antes de compilar se debe agregar a pypandoc en la funcion, `_convert_input` del archivo __init__.py, el flag para que no
se muestre la consola:

```    
    startupinfo = subprocess.STARTUPINFO()   # <--- Esta Linea
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW   # <--- Esta Linea

    p = subprocess.Popen(
        args,
        stdin=subprocess.PIPE if string_input else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=0x08000000,  # <--- Esta Linea
        startupinfo=startupinfo,  # <--- Esta Linea
        env=new_env)
```


## Borrar hook de excepción en main.py

## Compilar archivos sensibles

Posicionarse en la carpeta "ZondaPro" con el venv activado (deben estar instaladas las librerias de requeriments.txt) y correr el siguiente comando.
Se necesita tener instalado Visual Studio (No Visual Studio Code).

``` python setup.py build_ext --inplace ```

Esto va a generar archivos .pyd para los archivos indicados en "setup.py" y se borran los ".c".

Luego hay que hacer los archivos que se van a distribuir.

```python cx_setup.py build```

## Limpiar pyds

Correr el script "limpiar_pyds"

## Eliminar recursos

Eliminar la carpeta recursos dentro de build/exe***/lib/zondapro

## Instalador

Correr el archivo "iss.py" de la carpeta Inno Setup. Se va a generar un archivo llamado "setup.iss". Abrir este archivo con
Inno Setup y compilarlo para crear el instalador, el cual estara en la carpeta "Output" dentro de la carpeta Inno Setup.