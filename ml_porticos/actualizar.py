"""Publicación con respaldo y recuperación; sólo reemplaza archivos enumerados."""
from pathlib import Path
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
import io
import time
import shutil

def reemplazar(origen, destino):
    for intento in range(7):
        try:
            Path(origen).replace(destino)
            return
        except PermissionError:
            if intento == 6: raise
            time.sleep(min(.5*2**intento,4))

def publicar(temporal, salida, nombres):
    temporal, salida = Path(temporal).resolve(), Path(salida).resolve()
    if temporal == salida: raise ValueError('La preparación debe estar en una carpeta diferente.')
    if any(Path(n).name != n for n in nombres): raise ValueError('Sólo nombres simples permitidos.')
    if not all((temporal/n).is_file() for n in nombres): raise ValueError('Faltan resultados para publicar.')
    salida.mkdir(parents=True,exist_ok=True)
    respaldo=salida/('respaldo_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.zip')
    memoria=io.BytesIO()
    with ZipFile(memoria,'w',ZIP_DEFLATED) as z:
        for n in nombres:
            if (salida/n).exists(): z.writestr(n,(salida/n).read_bytes())
    respaldo.write_bytes(memoria.getvalue())
    cambiados=[]
    try:
        for n in nombres:
            # Conservar el original preparado hasta terminar toda la publicación.
            candidato=temporal/('publicar_'+n)
            shutil.copyfile(temporal/n,candidato)
            reemplazar(candidato,salida/n); cambiados.append(n)
    except OSError:
        with ZipFile(respaldo) as z:
            for n in reversed(cambiados):
                if n in z.namelist():
                    restaurar=temporal/('restaurar_'+n)
                    restaurar.write_bytes(z.read(n)); reemplazar(restaurar,salida/n)
                else:
                    (salida/n).unlink()
        raise
    for n in nombres:
        (temporal/n).unlink()
    # No se borran directorios recursivamente ni archivos ajenos a la ejecución.
    if not any(temporal.iterdir()): temporal.rmdir()
    return respaldo
