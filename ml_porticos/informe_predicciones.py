"""Presenta predicciones ya calculadas, sin entrenar ni cargar modelos."""
from pathlib import Path
import argparse
import csv
import html
import json
import webbrowser

import numpy as np
import pandas as pd

OBJETIVOS = {
    'Tx_s': ('Período X', 's'),
    'Ty_s': ('Período Y', 's'),
    'V_modal_ajustado_X_kgf': ('Cortante basal X', 'kgf'),
    'V_modal_ajustado_Y_kgf': ('Cortante basal Y', 'kgf'),
    'desplazamiento_techo_max_X_cm': ('Desplazamiento de techo X', 'cm'),
    'desplazamiento_techo_max_Y_cm': ('Desplazamiento de techo Y', 'cm'),
    'deriva_max_X': ('Deriva máxima X', 'adimensional'),
    'deriva_max_Y': ('Deriva máxima Y', 'adimensional'),
}


def formato(valor):
    if pd.isna(valor):
        return 'No aplicable (vacío)'
    if isinstance(valor, (bool, np.bool_)):
        return '1' if valor else '0'
    if isinstance(valor, (int, float, np.number)):
        return f'{valor:.10g}'
    return str(valor)


def detalle_individual(datos, pred):
    fila, estimaciones = datos.iloc[0], pred.iloc[0]
    columnas = json.loads((Path(__file__).resolve().parents[1] /
                          'resultados_ml_optimizado/variables_utilizadas.json').read_text(encoding='utf-8'))['entradas']
    faltantes = sorted(set(columnas) - set(datos.columns))
    if faltantes:
        raise ValueError('Faltan entradas del modelo en el Excel: ' + ', '.join(faltantes))
    referencia = any(k in datos and pd.notna(fila[k]) for k in OBJETIVOS)
    salidas = []
    for k, (nombre, unidad) in OBJETIVOS.items():
        valor = float(estimaciones[k + '_predicho'])
        salida = {'Resultado': nombre, 'Unidad': unidad, 'Predicción ML': formato(valor)}
        if referencia:
            real = float(fila[k]) if k in datos and pd.notna(fila[k]) else None
            if real is not None and np.isfinite(real):
                error = abs(valor - real)
                salida.update({'OpenSees': formato(real), 'Error absoluto': formato(error),
                               'Error relativo (%)': formato(100 * error / abs(real)) if real else 'No definido'})
            else:
                salida.update({'OpenSees': 'No disponible', 'Error absoluto': 'No disponible',
                               'Error relativo (%)': 'No disponible'})
        salidas.append(salida)
    partes = []
    if 'ID_familia' in datos:
        partes.append('<p>Familia: ' + html.escape(formato(fila['ID_familia'])) + '</p>')
    partes += ['<h2>Resultados de salida</h2>',
               pd.DataFrame(salidas).to_html(index=False, escape=True)]
    if referencia:
        partes.append('<p>OpenSees es la referencia calculada del Excel, no una medición de un edificio real.</p>')
    else:
        partes.append('<p>El Excel contiene entradas para predecir. No incluye respuestas de OpenSees, por lo que no se muestran errores frente a una referencia.</p>')
    partes += [f'<h2>Datos de entrada ({len(columnas)} variables)</h2>',
               '<p>Longitudes en cm; resistencia en kgf/cm²; peso en kgf; cargas superficiales en kgf/cm²; tiempo en s. Los vacíos representan elementos no aplicables.</p>',
               pd.DataFrame({'Variable': columnas,
                             'Valor de entrada': [formato(fila[k]) for k in columnas]}).to_html(index=False, escape=True)]
    return partes


def generar(excel, predicciones, salida, ident=None):
    excel, predicciones, salida = map(Path, (excel, predicciones, salida))
    with pd.ExcelFile(excel) as book:
        if len(book.sheet_names) != 1:
            raise ValueError('El Excel debe tener una sola hoja.')
        datos = pd.read_excel(book)
    with predicciones.open(encoding='utf-8-sig', newline='') as f:
        pred = pd.DataFrame(list(csv.DictReader(f)))
    if 'ID_estructura' not in datos or 'ID_estructura' not in pred:
        raise ValueError('El Excel y el CSV deben incluir ID_estructura.')
    for tabla in (datos, pred):
        ids = pd.to_numeric(tabla['ID_estructura'], errors='raise')
        if ids.isna().any() or ids.duplicated().any() or not np.isfinite(ids).all() or (ids % 1 != 0).any():
            raise ValueError('Los identificadores deben ser enteros, únicos y completos.')
        tabla['ID_estructura'] = ids.astype('int64')
    if set(datos.ID_estructura) != set(pred.ID_estructura):
        raise ValueError('El Excel y el CSV deben corresponder al mismo lote de estructuras.')
    for objetivo in OBJETIVOS:
        nombre = objetivo + '_predicho'
        if nombre not in pred:
            raise ValueError('Falta la predicción: ' + nombre)
        pred[nombre] = pred[nombre].map(float)
        if not np.isfinite(pred[nombre]).all():
            raise ValueError('Hay predicciones no finitas.')
    if 'ID_familia' in pred and 'ID_familia' in datos:
        familias = pred[['ID_estructura', 'ID_familia']].merge(
            datos[['ID_estructura', 'ID_familia']], on='ID_estructura', validate='one_to_one')
        if not (pd.to_numeric(familias.ID_familia_x) == pd.to_numeric(familias.ID_familia_y)).all():
            raise ValueError('Las familias del Excel y del CSV no coinciden.')
    if ident is not None:
        pred = pred.loc[pred.ID_estructura == ident].copy()
        datos = datos.loc[datos.ID_estructura == ident].copy()
        if len(pred) != 1:
            raise ValueError(f'ID {ident} no encontrado en este lote.')
    if salida.suffix.lower() != '.html':
        raise ValueError('La salida debe tener extensión .html.')
    if salida.resolve() in {excel.resolve(), predicciones.resolve()} or salida.exists():
        raise ValueError('La salida ya existe o coincide con un archivo de entrada. Elija otro nombre.')
    individual = len(pred) == 1
    if individual:
        ident = int(pred.iloc[0]['ID_estructura'])
    titulo = f'Estructura {ident}: predicción ML' if individual else f'Predicciones del lote: {len(pred)} estructuras'
    partes = ['<!doctype html><html lang="es"><meta charset="utf-8">',
              '<meta name="viewport" content="width=device-width, initial-scale=1">',
              '<title>' + html.escape(titulo) + '</title>',
              '<style>body{font:16px/1.5 Arial;max-width:1200px;margin:36px auto;padding:0 20px;color:#173042}table{border-collapse:collapse;margin:20px 0;width:100%}th,td{padding:10px;border:1px solid #dce2e7;text-align:left}th{background:#e8eff5}h1,h2{color:#17365d}.tabla{overflow:auto}</style>',
              '<h1>' + html.escape(titulo) + '</h1>',
              '<p>Este informe presenta las predicciones del CSV indicado; no vuelve a calcular ni entrena el modelo.</p>',
              '<p>Excel: ' + html.escape(excel.name) + '. Predicciones: ' + html.escape(predicciones.name) + '.</p>',
              '<p>Los ID son locales a cada lote. Use siempre el Excel y el CSV de la misma ejecución. La coincidencia de ID no verifica por sí sola que los archivos correspondan a las mismas entradas.</p>']
    if individual:
        partes += detalle_individual(datos, pred)
        partes.append('</html>')
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text('\n'.join(partes), encoding='utf-8')
        return salida.resolve()
    columnas = ['ID_estructura'] + (['ID_familia'] if 'ID_familia' in pred else []) + [k + '_predicho' for k in OBJETIVOS]
    nombres = {k + '_predicho': f'{nombre} ({unidad})' for k, (nombre, unidad) in OBJETIVOS.items()}
    partes += ['<h2>Predicciones</h2><div class="tabla">',
               pred[columnas].rename(columns=nombres).to_html(index=False, float_format=lambda v: f'{v:.10g}'), '</div>']
    disponibles = [k for k in OBJETIVOS if k in datos]
    if disponibles:
        partes += ['<h2>Comparación con los resultados calculados</h2>',
                   '<p>OpenSees es una referencia de simulación, no una medición de un edificio real. Se leen los resultados presentes en el Excel. La comparación no cambia las predicciones.</p>']
        merged = pred.merge(datos[['ID_estructura'] + disponibles], on='ID_estructura', validate='one_to_one')
        for k in disponibles:
            real = pd.to_numeric(merged[k], errors='raise')
            if not np.isfinite(real).all():
                continue
            estimado = merged[k + '_predicho']
            error = abs(estimado - real)
            tabla = pd.DataFrame({'ID_estructura': merged.ID_estructura, 'OpenSees': real,
                                  'Predicción ML': estimado, 'Error absoluto': error,
                                  'Error relativo (%)': 100 * error / abs(real).replace(0, np.nan)})
            nombre, unidad = OBJETIVOS[k]
            partes += ['<h3>' + html.escape(f'{nombre} ({unidad})') + '</h3><div class="tabla">',
                       tabla.to_html(index=False, float_format=lambda v: f'{v:.10g}', na_rep='No definido'), '</div>']
    else:
        partes.append('<p>El Excel no contiene respuestas de referencia; se muestran únicamente las predicciones.</p>')
    partes.append('</html>')
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text('\n'.join(partes), encoding='utf-8')
    return salida.resolve()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--excel', required=True)
    p.add_argument('--predicciones', required=True)
    p.add_argument('--salida', required=True)
    p.add_argument('--id', type=int)
    p.add_argument('--abrir', action='store_true')
    a = p.parse_args()
    archivo = generar(a.excel, a.predicciones, a.salida, a.id)
    print(f'Informe: {archivo}')
    if a.abrir:
        webbrowser.open(archivo.as_uri())


if __name__ == '__main__':
    try:
        main()
    except (ValueError, FileNotFoundError, PermissionError, KeyError) as exc:
        raise SystemExit(f'ERROR: {exc}')
