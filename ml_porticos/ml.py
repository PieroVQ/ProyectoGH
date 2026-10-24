"""Random Forest independiente del análisis OpenSees. Ejecutar con --help."""
import argparse
import hashlib
import json
from pathlib import Path
import importlib.metadata
import html
import io
import tempfile
import copy
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import GroupShuffleSplit, GroupKFold, cross_val_predict
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.inspection import permutation_importance

OBJETIVOS = ['Tx_s','Ty_s','V_modal_ajustado_X_kgf','V_modal_ajustado_Y_kgf',
             'desplazamiento_techo_max_X_cm','desplazamiento_techo_max_Y_cm',
             'deriva_max_X','deriva_max_Y']
VANOS_ORDENADOS=[f'luz_{e}_{i}_cm' for e in ('X','Y') for i in range(1,6)]
ARCHIVOS_ML=['division.csv','metricas.csv','importancias.csv','predicciones_prueba.csv',
             'informe.html','modelo_evaluacion.joblib','modelo_final.joblib','resumen.json','variables_utilizadas.json']

def guardar_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')

def guardar_modelo(path, paquete):
    # Una sola escritura evita miles de escrituras pequeñas en unidades lentas.
    memoria=io.BytesIO()
    joblib.dump(paquete,memoria,compress=3)
    Path(path).write_bytes(memoria.getvalue())

def leer(path):
    with pd.ExcelFile(path) as libro:
        if len(libro.sheet_names) != 1:
            raise ValueError('Se espera un Excel con una sola hoja.')
        return pd.read_excel(libro)

def numericos(df, nombres):
    faltan = sorted(set(nombres)-set(df.columns))
    if faltan: raise ValueError(f'Faltan columnas: {faltan}')
    x = df[nombres].apply(pd.to_numeric, errors='raise').astype(float)
    if np.isinf(x.to_numpy()).any(): raise ValueError('Hay valores infinitos.')
    return x

def separar(grupos, semilla):
    if grupos.isna().any() or grupos.nunique()<8:
        raise ValueError('Se requieren al menos 8 familias identificadas sin ausencias.')
    tr, te = next(GroupShuffleSplit(n_splits=1,test_size=.25,random_state=semilla).split(grupos,groups=grupos))
    assert not set(grupos.iloc[tr]) & set(grupos.iloc[te])
    return tr, te

def modelo(arboles, semilla):
    # Ajuste del imputador exclusivamente dentro del entrenamiento de cada fold.
    return make_pipeline(SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True),
                         RandomForestRegressor(n_estimators=arboles,min_samples_leaf=2,
                                               max_features=.8,random_state=semilla,n_jobs=1))

def metricas(y, pred):
    return {'MAE':float(mean_absolute_error(y,pred)),
            'RMSE':float(np.sqrt(mean_squared_error(y,pred))),
            'R2':float(r2_score(y,pred)) if len(y)>1 and np.var(y)>0 else None}

def entrenar(a):
    if a.arboles<10 or a.repeticiones<1: raise ValueError('Use >=10 árboles y >=1 repetición.')
    origen=Path(a.excel).resolve(); df=leer(origen)
    manifiesto=Path(a.variables) if a.variables else origen.with_name('variables_ml.json')
    spec=json.loads(manifiesto.read_text(encoding='utf-8-sig'))
    nombres=list(dict.fromkeys(spec['entradas_iniciales']+VANOS_ORDENADOS))
    # Lista explícita del generador: no se admiten resultados ni identificadores.
    permitidos={'fc_kgf_cm2','fy_kgf_cm2','pisos','vanos_X','vanos_Y','Lx_cm','Ly_cm',
                'altura_total_cm','piso1_altura_cm','piso2_altura_cm','luz_media_X_cm','luz_media_Y_cm',
                'CV_luces_X','CV_luces_Y','U','Z','S','TP_s','TL_s','qv_piso_kgf_cm2',
                'acabados_kgf_cm2','tabiques_fijos_kgf_cm2','peso_sismico_kgf',
                't_maciza_cm','t_aligerada_cm','fraccion_area_maciza','cantidad_bloques','piso_inicio_bloque2'}
    permitidos.update(k for k in df.columns if k.startswith(('col_','viga_')) and k.endswith('_cm'))
    permitidos.update(VANOS_ORDENADOS)
    if set(nombres)-permitidos: raise ValueError('El manifiesto contiene entradas no autorizadas o resultados.')
    if 'fc_kgf_cm2' not in nombres: raise ValueError('Incluya fc_kgf_cm2 en entradas_iniciales.')
    x=numericos(df,nombres); y=numericos(df,OBJETIVOS)
    validar_vanos(x)
    if y.isna().any().any(): raise ValueError('Hay resultados ausentes; no se imputan objetivos.')
    if df['ID_estructura'].isna().any() or df['ID_estructura'].duplicated().any():
        raise ValueError('ID_estructura debe ser único y no vacío. No concatene bases sin reasignar IDs/familias.')
    g=df['ID_familia']; tr,te=separar(g,a.semilla)
    out=Path(a.salida)
    if out.exists() and any(out.iterdir()): raise ValueError('La salida ya contiene archivos. Elija otra carpeta.')
    out.mkdir(parents=True,exist_ok=True)
    xt,xe=x.iloc[tr],x.iloc[te]; gt=g.iloc[tr]
    cv=GroupKFold(n_splits=min(5,gt.nunique()))
    division=df[['ID_estructura','ID_familia']].copy(); division['conjunto']='entrenamiento'
    division.loc[te,'conjunto']='prueba'; division.to_csv(out/'division.csv',index=False)
    medidas=[]; importancias=[]; predicciones=df.iloc[te][['ID_estructura','ID_familia']].copy()
    evaluados={}; finales={}
    for target in OBJETIVOS:
        print(f'Entrenando {target}...',flush=True)
        yt=y.iloc[tr][target]; ye=y.iloc[te][target]
        est=modelo(a.arboles,a.semilla)
        oof=cross_val_predict(est,xt,yt,groups=gt,cv=cv,n_jobs=1)
        medidas.append({'objetivo':target,'conjunto':'validacion_cruzada_entrenamiento',**metricas(yt,oof)})
        est.fit(xt,yt); pred=est.predict(xe)
        medidas.append({'objetivo':target,'conjunto':'prueba_familias_reservadas',**metricas(ye,pred)})
        medidas.append({'objetivo':target,'conjunto':'baseline_media_entrenamiento',**metricas(ye,np.full(len(ye),yt.mean()))})
        predicciones[target+'_real']=ye.to_numpy(); predicciones[target+'_predicho']=pred
        # Incremento de MAE al permutar cada entrada original; valores negativos se conservan.
        imp=permutation_importance(est,xe,ye,scoring='neg_mean_absolute_error',
                                   n_repeats=a.repeticiones,random_state=a.semilla,n_jobs=1)
        for k,mean,std in zip(nombres,imp.importances_mean,imp.importances_std):
            importancias.append({'objetivo':target,'variable':k,'aumento_MAE':float(mean),'desviacion':float(std)})
        evaluados[target]=est
        finales[target]=modelo(a.arboles,a.semilla).fit(x,y[target])
    pd.DataFrame(medidas).to_csv(out/'metricas.csv',index=False)
    pd.DataFrame(importancias).to_csv(out/'importancias.csv',index=False)
    predicciones.to_csv(out/'predicciones_prueba.csv',index=False)
    tabla=pd.DataFrame(medidas)
    partes=['<!doctype html><html lang="es"><meta charset="utf-8"><title>Resultados Random Forest</title>',
            '<style>body{font:16px Arial;margin:40px;max-width:1200px}table{border-collapse:collapse;margin:20px 0}td,th{padding:9px;border:1px solid #ddd}th{background:#e5edf5}h2{margin-top:40px}</style>',
            '<h1>Evaluación del Random Forest</h1>',
            '<p>Familias de prueba separadas del entrenamiento. R² puede ser negativo. Compare con la referencia de la media; menor MAE/RMSE es mejor.</p>',
            tabla.to_html(index=False,float_format=lambda v:f'{v:.6g}'),
            '<h1>Variables por objetivo</h1><p>Importancia = incremento de MAE al permutar. No es causalidad ni porcentaje. Variables correlacionadas pueden compartir importancia. Un modelo impreciso no permite interpretar estas posiciones con confianza.</p>']
    for target in OBJETIVOS:
        top=pd.DataFrame(importancias).query('objetivo == @target').sort_values('aumento_MAE',ascending=False).head(15)
        partes.extend(['<h2>'+html.escape(target)+'</h2>',top[['variable','aumento_MAE','desviacion']].to_html(index=False,float_format=lambda v:f'{v:.6g}')])
    partes.append('</html>')
    (out/'informe.html').write_text('\n'.join(partes),encoding='utf-8')
    dominio={k:{'min':float(x[k].min()) if x[k].notna().any() else None,
                'max':float(x[k].max()) if x[k].notna().any() else None,
                'valores':sorted(x[k].dropna().unique().tolist()) if x[k].nunique()<=10 else None,
                'admite_ausencia':bool(x[k].isna().any())} for k in nombres}
    datos={'entradas':nombres,'objetivos':OBJETIVOS,'dominio':dominio}
    guardar_modelo(out/'modelo_evaluacion.joblib',{**datos,'modelos':evaluados})
    guardar_modelo(out/'modelo_final.joblib',{**datos,'modelos':finales})
    resumen={'filas':len(df),'familias':int(g.nunique()),'filas_entrenamiento':len(tr),'filas_prueba':len(te),
             'familias_prueba':int(g.iloc[te].nunique()),'semilla':a.semilla,'arboles':a.arboles,
             'repeticiones_importancia':a.repeticiones,'excel_sha256':hashlib.sha256(origen.read_bytes()).hexdigest(),
             'constantes_entrenamiento':[k for k in nombres if xt[k].nunique(dropna=False)<=1],
             'fc_entrenamiento':sorted(xt.fc_kgf_cm2.unique().tolist()),'fc_prueba':sorted(xe.fc_kgf_cm2.unique().tolist()),
             'versiones':{k:importlib.metadata.version(k) for k in ['scikit-learn','numpy','pandas','joblib']},
             'nota':'Métricas e importancias corresponden al modelo de evaluación. Modelo final reajustado con toda la base; no tiene prueba independiente nueva. Importancias no causales; correlaciones pueden repartir u ocultar importancia.'}
    guardar_json(out/'resumen.json',resumen); guardar_json(out/'variables_utilizadas.json',datos)
    print(pd.DataFrame(medidas).query("conjunto == 'prueba_familias_reservadas'").to_string(index=False))
    print(f'Resultados guardados en {out.resolve()}')

def validar_vanos(x):
    for eje in ('X','Y'):
        cantidad=x[f'vanos_{eje}']
        if not cantidad.isin(range(2,6)).all(): raise ValueError('Cantidad de vanos inválida.')
        for i in range(1,6):
            v=x[f'luz_{eje}_{i}_cm']; activo=cantidad>=i
            if v[activo].isna().any() or (v[activo]<=0).any() or v[~activo].notna().any():
                raise ValueError(f'Luces {eje}: complete vanos existentes y deje vacíos los inexistentes.')
        total=x[[f'luz_{eje}_{i}_cm' for i in range(1,6)]].sum(axis=1)
        if not np.allclose(total,x[f'L{eje.lower()}_cm'],rtol=1e-8,atol=1e-6):
            raise ValueError(f'La suma de vanos {eje} no coincide con la dimensión total.')

def entrenar_actualizando(a):
    if not a.reemplazar: return entrenar(a)
    salida=Path(a.salida).resolve(); salida.parent.mkdir(parents=True,exist_ok=True)
    temporal=Path(tempfile.mkdtemp(prefix='preparando_ml_',dir=salida.parent))
    nuevo=copy.copy(a); nuevo.salida=str(temporal)
    try:
        entrenar(nuevo)
        from actualizar import publicar
        respaldo=publicar(temporal,salida,ARCHIVOS_ML)
        print(f'Actualizado: {salida}. Respaldo: {respaldo.name}')
    except Exception:
        print(f'Preparación conservada en {temporal}; revise el error antes de continuar.')
        raise

def optimizar_actualizando(a):
    from optimizar import ejecutar
    from threadpoolctl import threadpool_limits
    if not a.reemplazar:
        with threadpool_limits(limits=4): return ejecutar(a)
    salida=Path(a.salida).resolve();salida.parent.mkdir(parents=True,exist_ok=True)
    temporal=Path(tempfile.mkdtemp(prefix='preparando_optimizacion_',dir=salida.parent))
    nuevo=copy.copy(a);nuevo.salida=str(temporal)
    try:
        with threadpool_limits(limits=4): ejecutar(nuevo)
        from actualizar import publicar
        extras=['comparacion_configuraciones.csv','comparacion_conjunta.csv','seleccion.json',
                'curva_aprendizaje.csv','modelos_mejorados.py']
        respaldo=publicar(temporal,salida,ARCHIVOS_ML+extras)
        print(f'Modelo optimizado actualizado: {salida}. Respaldo: {respaldo.name}')
    except Exception:
        print(f'Preparación conservada en {temporal}.');raise

def predecir(a):
    # Cargar únicamente modelos de confianza: joblib puede ejecutar código al deserializar.
    paquete=joblib.load(a.modelo); df=leer(a.excel); x=numericos(df,paquete['entradas'])
    if all(k in x for k in VANOS_ORDENADOS): validar_vanos(x)
    avisos=[]
    for k,d in paquete['dominio'].items():
        if not d['admite_ausencia'] and x[k].isna().any(): avisos.append(k+': dato ausente no observado')
        v=x[k].dropna()
        if len(v) and (d['min'] is None or v.min()<d['min'] or v.max()>d['max']): avisos.append(k+': fuera del rango entrenado')
        if k in ('fc_kgf_cm2','fy_kgf_cm2','U','Z','pisos') and d['valores'] is not None and not v.isin(d['valores']).all():
            avisos.append(k+': valor no entrenado')
    if avisos: raise ValueError('Predicción rechazada: '+'; '.join(avisos))
    out=Path(a.salida)
    if out.exists(): raise ValueError('El archivo de salida ya existe.')
    out.parent.mkdir(parents=True,exist_ok=True)
    resultado=df[[k for k in ['ID_estructura','ID_familia'] if k in df]].copy()
    for k,est in paquete['modelos'].items(): resultado[k+'_predicho']=est.predict(x)
    resultado.to_csv(out,index=False); print(f'Predicciones: {out.resolve()}')

def main():
    p=argparse.ArgumentParser(description='Random Forest para el Excel de pórticos. Sin OpenSees.')
    sub=p.add_subparsers(dest='accion',required=True)
    t=sub.add_parser('entrenar'); t.add_argument('--excel',required=True); t.add_argument('--variables')
    t.add_argument('--salida',default='resultados_ml'); t.add_argument('--semilla',type=int,default=42)
    t.add_argument('--arboles',type=int,default=200); t.add_argument('--repeticiones',type=int,default=5)
    t.add_argument('--reemplazar',action='store_true',help='Actualizar la misma carpeta con respaldo automático')
    t=sub.add_parser('predecir'); t.add_argument('--modelo',required=True); t.add_argument('--excel',required=True)
    t.add_argument('--salida',default='predicciones_ml.csv')
    t=sub.add_parser('optimizar',help='Comparar modelos y elegir la mejor combinación por respuesta')
    t.add_argument('--excel',required=True);t.add_argument('--salida',default='resultados_ml')
    t.add_argument('--semilla',type=int,default=48371);t.add_argument('--reemplazar',action='store_true')
    a=p.parse_args()
    if a.accion=='optimizar': optimizar_actualizando(a)
    elif a.accion=='entrenar': entrenar_actualizando(a)
    else: predecir(a)

if __name__=='__main__':
    try: main()
    except (ValueError,FileNotFoundError,PermissionError,KeyError) as exc:
        raise SystemExit(f'ERROR: {exc}')
