"""Base nueva con familias independientes; análisis aislados en procesos."""
from pathlib import Path
import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'porticos_rc'))
from porticos.geometria import generar_familia,validar_config
from porticos.generador import preparar
from porticos.analisis import analizar
from porticos.datos import a_fila,exportar,diccionario

def calcular(tarea):
    c,f=tarea
    try:
        b=preparar(generar_familia(c,f),c);a=analizar(b)
        if not a['regularidad_evaluable']: return None,{'familia':f,'estado':'irregularidad_detectada'}
        return a_fila(b,a,0),None
    except Exception as exc:
        return None,{'familia':f,'estado':'fallo','motivo':str(exc)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--cantidad',type=int,default=1500)
    p.add_argument('--semilla',type=int,default=20261119);p.add_argument('--procesos',type=int,default=4)
    p.add_argument('--salida',default='base_ml_ampliada');a=p.parse_args()
    if a.cantidad<20 or not 1<=a.procesos<=8: raise ValueError('Cantidad >=20 y procesos de 1 a 8.')
    out=Path(a.salida);out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()): raise ValueError('La carpeta contiene archivos. Use una salida vacía.')
    c=json.loads((Path(__file__).resolve().parents[1]/'porticos_rc/config.json').read_text(encoding='utf-8'))
    c.update(cantidad=a.cantidad,semilla=a.semilla,variantes_por_familia=1,max_intentos=a.cantidad*20)
    validar_config(c);(out/'configuracion_base.json').write_text(json.dumps(c,indent=2),encoding='utf-8')
    rows=[];f=1;inicio=time.monotonic()
    with ProcessPoolExecutor(max_workers=a.procesos) as pool, (out/'descartes.jsonl').open('w',encoding='utf-8') as log:
        while len(rows)<a.cantidad and f<c['max_intentos']:
            batch=list(range(f,min(f+32,c['max_intentos']+1)))
            for fila,error in pool.map(calcular,[(c,i) for i in batch]):
                if error: log.write(json.dumps(error,ensure_ascii=False)+'\n')
                elif len(rows)<a.cantidad:
                    fila['ID_estructura']=len(rows)+1;rows.append(fila)
            f+=len(batch);log.flush()
            print(f'{len(rows)}/{a.cantidad} familias válidas; {f-1} intentos; {time.monotonic()-inicio:.0f} s',flush=True)
            if len(rows)%100<32 or len(rows)==a.cantidad:
                exportar(rows,out/'estructuras.xlsx');diccionario(rows,out/'diccionario_columnas.json')
        exportar(rows,out/'estructuras.xlsx');diccionario(rows,out/'diccionario_columnas.json')
    if len(rows)!=a.cantidad: raise ValueError('No se alcanzó la cantidad; revise descartes.')
    (out/'resumen_base.json').write_text(json.dumps({'estructuras':len(rows),'familias':len(rows),
        'semilla':a.semilla,'intentos':f-1,'segundos':time.monotonic()-inicio,
        'nota':'Una alternativa por familia. Base independiente para selección y prueba ML; no usa checkpoints del generador habitual.'},indent=2),encoding='utf-8')

if __name__=='__main__': main()
