"""Comparación individual con el modelo de evaluación (no el reajustado)."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import webbrowser
import joblib
import numpy as np
import pandas as pd
from ml import leer, numericos, validar_vanos, VANOS_ORDENADOS

NOMBRES={
    'Tx_s':('Período X','s'), 'Ty_s':('Período Y','s'),
    'V_modal_ajustado_X_kgf':('Cortante basal X','kgf'),
    'V_modal_ajustado_Y_kgf':('Cortante basal Y','kgf'),
    'desplazamiento_techo_max_X_cm':('Desplazamiento máximo de techo X','cm'),
    'desplazamiento_techo_max_Y_cm':('Desplazamiento máximo de techo Y','cm'),
    'deriva_max_X':('Deriva máxima X','adimensional'),
    'deriva_max_Y':('Deriva máxima Y','adimensional')}

def formato(v):
    if pd.isna(v): return 'No aplicable (vacío)'
    return f'{v:.6g}' if isinstance(v,(int,float,np.number)) else str(v)

def informe(excel, modelos, ident, salida=None):
    excel=Path(excel); modelos=Path(modelos)
    resumen=json.loads((modelos/'resumen.json').read_text(encoding='utf-8'))
    if hashlib.sha256(excel.read_bytes()).hexdigest()!=resumen['excel_sha256']:
        raise ValueError('El Excel cambió desde el entrenamiento. Use el Excel original o vuelva a entrenar antes de comparar.')
    division=pd.read_csv(modelos/'division.csv')
    seleccion=division.loc[division.ID_estructura==ident]
    if len(seleccion)!=1: raise ValueError(f'ID {ident} no encontrado en la división guardada.')
    conjunto=seleccion.iloc[0]['conjunto']
    df=leer(excel); fila=df.loc[df.ID_estructura==ident]
    if len(fila)!=1: raise ValueError('El identificador debe aparecer exactamente una vez en Excel.')
    # Usar sólo archivos joblib de confianza. El modelo de evaluación no vio las familias de prueba.
    paquete=joblib.load(modelos/'modelo_evaluacion.joblib')
    x=numericos(fila,paquete['entradas'])
    if all(k in x for k in VANOS_ORDENADOS): validar_vanos(x)
    comparacion=[]
    for objetivo in paquete['objetivos']:
        real=float(fila.iloc[0][objetivo]); estimado=float(paquete['modelos'][objetivo].predict(x)[0])
        if not np.isfinite(real): raise ValueError('El resultado de OpenSees está ausente o no es finito.')
        error=abs(estimado-real)
        nombre,unidad=NOMBRES[objetivo]
        comparacion.append({'Resultado':nombre,'Unidad':unidad,'OpenSees':formato(real),
                            'Predicción ML':formato(estimado),'Error absoluto':formato(error),
                            'Error relativo (%)':formato(100*error/abs(real)) if real!=0 else 'No definido: referencia cero'})
    entradas=pd.DataFrame({'Variable':paquete['entradas'],'Valor de entrada':[formato(x.iloc[0][k]) for k in paquete['entradas']]})
    aviso=('Este caso quedó reservado para prueba: el modelo de evaluación no utilizó su familia para aprender.'
           if conjunto=='prueba' else
           'Este caso participó en el entrenamiento. La comparación no demuestra precisión en edificios nuevos; elija un ID de prueba para evaluarla.')
    ids=division.loc[division.conjunto=='prueba','ID_estructura'].astype(int).tolist()
    contenido=f'''<!doctype html><html lang="es"><meta charset="utf-8">
<title>Estructura {ident}: comparación ML</title>
<style>body{{font:16px Arial;max-width:1200px;margin:36px auto;padding:0 20px;color:#173042}}table{{border-collapse:collapse;width:100%;margin:20px 0}}th,td{{border:1px solid #dce2e7;padding:10px;text-align:left}}th{{background:#e8eff5}}.aviso{{background:#fff1c9;padding:16px;line-height:1.5}}h1,h2{{color:#17365d}}</style>
<h1>Estructura {ident}</h1>
<p>Familia: {int(fila.iloc[0]['ID_familia'])} · Conjunto: {html.escape(conjunto)}</p>
<p class="aviso">{aviso}</p>
<h2>Predicciones frente al análisis estructural</h2>
<p>OpenSees es la referencia calculada; no son mediciones de un edificio real. Se usa modelo_evaluacion.joblib, no el modelo final reajustado con toda la base.</p>
{pd.DataFrame(comparacion).to_html(index=False,escape=True)}
<p>Error absoluto = diferencia entre predicción y referencia, sin signo. Error relativo = error absoluto / magnitud de la referencia × 100. No se calcula R² para una sola estructura.</p>
<h2>Datos que entraron al modelo</h2>
<p>Longitudes en cm; resistencia en kgf/cm²; peso en kgf; cargas superficiales en kgf/cm²; tiempos en s. Los vanos mantienen su orden. Los vacíos representan elementos inexistentes; el tratamiento de ausencias está guardado dentro del modelo.</p>
{entradas.to_html(index=False,escape=True)}
<p>Identificadores reservados para prueba: {', '.join(map(str,ids))}.</p>
<p>Excel utilizado: {html.escape(excel.name)}. Las predicciones heredan las hipótesis y límites de la base de entrenamiento.</p></html>'''
    destino=Path(salida) if salida else modelos/f'caso_{ident:04d}.html'
    protegidos={excel.resolve(),(modelos/'modelo_evaluacion.joblib').resolve(),(modelos/'modelo_final.joblib').resolve()}
    if destino.suffix.lower()!='.html' or destino.resolve() in protegidos: raise ValueError('La salida debe ser un archivo HTML independiente.')
    destino.parent.mkdir(parents=True,exist_ok=True)
    destino.write_text(contenido,encoding='utf-8')
    return destino.resolve()

def main():
    p=argparse.ArgumentParser(description='Ver entradas y comparación individual con OpenSees')
    p.add_argument('--excel',required=True);p.add_argument('--modelos',default='resultados_ml')
    p.add_argument('--id',type=int,required=True);p.add_argument('--html');p.add_argument('--abrir',action='store_true')
    a=p.parse_args();archivo=informe(a.excel,a.modelos,a.id,a.html)
    print(f'Informe: {archivo}')
    if a.abrir: webbrowser.open(archivo.as_uri())

if __name__=='__main__':
    try: main()
    except (ValueError,FileNotFoundError,PermissionError,KeyError) as exc: raise SystemExit(f'ERROR: {exc}')
