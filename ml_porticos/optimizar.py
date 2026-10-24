"""Selección por validación cruzada y evaluación final en familias reservadas."""
from pathlib import Path
import argparse
import json
import hashlib
import importlib.metadata
import time
import html
import shutil
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit,GroupKFold
from sklearn.metrics import mean_squared_error
from threadpoolctl import threadpool_limits
from ml import OBJETIVOS,VANOS_ORDENADOS,leer,numericos,validar_vanos,metricas,guardar_json,guardar_modelo
from modelos_mejorados import CONFIGURACIONES,RespuestaRegressor,PromedioModelos

def entradas(df,spec):
    # Pesos/centros son metrados de geometría y cargas, no respuestas sísmicas.
    adicionales=['qv_cubierta_kgf_cm2']+VANOS_ORDENADOS
    for k in range(1,6):
        adicionales += [f'piso{k}_{s}' for s in ('altura_cm','peso_sismico_kgf','CM_X_cm','CM_Y_cm','inercia_peso_kgf_cm2')]
    adicionales += [f'paño_X{i}_Y{j}_macizo' for i in range(1,6) for j in range(1,6)]
    nombres=list(dict.fromkeys(spec['entradas_iniciales']+adicionales))
    # Impedir que un manifiesto modificado añada respuestas o identificadores.
    forbidden=('Tx','Ty','V_','desplazamiento','deriva','modo','error','regularidad','ID_')
    if any(k.startswith(forbidden) or 'rigidez' in k or 'cortante' in k for k in nombres):
        raise ValueError('El manifiesto incluye resultados que producirían fuga de información.')
    x=numericos(df,nombres);validar_vanos(x)
    return x

def rmse(y,p): return float(np.sqrt(mean_squared_error(y,p)))

def construir(obj,componentes,x,y,seed):
    modelos=[RespuestaRegressor(obj,c,seed).fit(x,y) for c in componentes]
    return modelos[0] if len(modelos)==1 else PromedioModelos(modelos)

def ejecutar(a):
    inicio=time.monotonic();out=Path(a.salida)
    if out.exists() and any(out.iterdir()): raise ValueError('Use una carpeta de salida vacía para conservar la auditoría de selección.')
    out.mkdir(parents=True,exist_ok=True)
    origen=Path(a.excel).resolve();df=leer(origen)
    spec=json.loads(origen.with_name('variables_ml.json').read_text(encoding='utf-8'))
    x=entradas(df,spec);y=numericos(df,OBJETIVOS);g=df.ID_familia
    if y.isna().any().any() or (y<=0).any().any(): raise ValueError('Los objetivos deben ser completos y positivos.')
    if df.ID_estructura.duplicated().any() or g.isna().any() or g.nunique()<100:
        raise ValueError('Se requieren >=100 familias, ID únicos y familias no vacías.')
    tr,te=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=a.semilla).split(x,groups=g))
    assert not set(g.iloc[tr]) & set(g.iloc[te])
    xt=x.iloc[tr].reset_index(drop=True);yt=y.iloc[tr].reset_index(drop=True);gt=g.iloc[tr].reset_index(drop=True)
    xe=x.iloc[te];ye=y.iloc[te]
    division=df[['ID_estructura','ID_familia']].copy();division['conjunto']='entrenamiento';division.loc[te,'conjunto']='prueba'
    division.to_csv(out/'division.csv',index=False)
    folds=list(GroupKFold(n_splits=3).split(xt,groups=gt))
    oof={};resultados=[]
    for nombre in CONFIGURACIONES:
        oof[nombre]=np.empty(yt.shape)
        for j,obj in enumerate(OBJETIVOS):
            print(f'Validación: {nombre} / {obj}',flush=True)
            for ia,iv in folds:
                est=RespuestaRegressor(obj,nombre,a.semilla).fit(xt.iloc[ia],yt.iloc[ia,j])
                oof[nombre][iv,j]=est.predict(xt.iloc[iv])
            met=metricas(yt.iloc[:,j],oof[nombre][:,j]);met['NRMSE']=met['RMSE']/float(yt.iloc[:,j].std(ddof=0))
            met.update(configuracion=nombre,objetivo=obj);resultados.append(met)
        pd.DataFrame(resultados).to_csv(out/'comparacion_configuraciones.csv',index=False)
        print(f'{nombre} terminado; {time.monotonic()-inicio:.0f} segundos',flush=True)
    # Selección antes de mirar cualquier resultado de prueba.
    seleccion={};oof_elegido=np.empty(yt.shape)
    for j,obj in enumerate(OBJETIVOS):
        orden=sorted(CONFIGURACIONES,key=lambda c:rmse(yt.iloc[:,j],oof[c][:,j]))
        candidatos=[([c],oof[c][:,j]) for c in orden]
        for n in (2,3): candidatos.append((orden[:n],np.mean([oof[c][:,j] for c in orden[:n]],axis=0)))
        componentes,pred=min(candidatos,key=lambda par:rmse(yt.iloc[:,j],par[1]))
        seleccion[obj]=componentes;oof_elegido[:,j]=pred
    scores=[]
    for nombre,pred in [*oof.items(),('Seleccion_por_respuesta',oof_elegido)]:
        valores=[rmse(yt.iloc[:,j],pred[:,j])/yt.iloc[:,j].std(ddof=0) for j in range(8)]
        scores.append({'configuracion':nombre,'NRMSE_promedio':float(np.mean(valores)),
                       'NRMSE_peor_respuesta':float(max(valores)),
                       'criterio_conjunto':float(np.mean(valores)+.25*max(valores))})
    pd.DataFrame(scores).sort_values('criterio_conjunto').to_csv(out/'comparacion_conjunta.csv',index=False)
    guardar_json(out/'seleccion.json',{'modelos_por_objetivo':seleccion,'criterio':'Menor RMSE en predicciones fuera de muestra de 3 folds por familia. Promedios de los 2/3 mejores sólo si reducen ese error. La selección por respuesta minimiza también el promedio NRMSE + 0.25 peor NRMSE.',
                                     'configuraciones':CONFIGURACIONES,'semilla':a.semilla})
    modelos={};finales={};medidas=[];comparacion=df.iloc[te][['ID_estructura','ID_familia']].copy();baselines={}
    # Curva de aprendizaje sólo dentro del desarrollo; no usa las familias de prueba final.
    aprendizaje=[]
    ia,iv=folds[0]
    orden_muestra=np.random.default_rng(a.semilla).permutation(ia)
    for j,obj in enumerate(OBJETIVOS):
        for tam in sorted(set([min(len(ia),n) for n in (100,300,600,len(ia))])):
            idx=orden_muestra[:tam]
            est=construir(obj,seleccion[obj],xt.iloc[idx],yt.iloc[idx,j],a.semilla)
            aprendizaje.append({'objetivo':obj,'filas_entrenamiento':tam,**metricas(yt.iloc[iv,j],est.predict(xt.iloc[iv]))})
        print(f'Ajuste seleccionado y prueba final: {obj}',flush=True)
        modelos[obj]=construir(obj,seleccion[obj],xt,yt.iloc[:,j],a.semilla)
        pred=modelos[obj].predict(xe)
        base=RespuestaRegressor(obj,'RF_original',a.semilla).fit(xt,yt.iloc[:,j])
        baselines[obj]=base.predict(xe)
        for nombre,real,pr in [('validacion_cruzada_entrenamiento',yt.iloc[:,j],oof_elegido[:,j]),
                               ('prueba_familias_reservadas',ye.iloc[:,j],pred),
                               ('RF_directo_misma_base',ye.iloc[:,j],baselines[obj]),
                               ('baseline_media_entrenamiento',ye.iloc[:,j],np.full(len(te),yt.iloc[:,j].mean()))]:
            med=metricas(real,pr);rel=np.abs(pr-np.asarray(real))/np.asarray(real)*100
            med.update(objetivo=obj,conjunto=nombre,error_relativo_mediano_pct=float(np.median(rel)),error_relativo_p90_pct=float(np.quantile(rel,.9)))
            medidas.append(med)
        comparacion[obj+'_real']=ye.iloc[:,j].to_numpy();comparacion[obj+'_predicho']=pred
        finales[obj]=construir(obj,seleccion[obj],x,y.iloc[:,j],a.semilla)
    pd.DataFrame(aprendizaje).to_csv(out/'curva_aprendizaje.csv',index=False)
    tabla=pd.DataFrame(medidas);tabla.to_csv(out/'metricas.csv',index=False);comparacion.to_csv(out/'predicciones_prueba.csv',index=False)
    # Importancia en prueba: diagnóstico posterior, no modifica la selección.
    importancias=[];rng=np.random.default_rng(a.semilla)
    for j,obj in enumerate(OBJETIVOS):
        print(f'Importancias: {obj}',flush=True)
        base_error=metricas(ye.iloc[:,j],comparacion[obj+'_predicho'])['MAE']
        for k in x.columns:
            delta=[]
            for _ in range(3):
                xp=xe.copy();xp[k]=rng.permutation(xp[k].to_numpy())
                delta.append(metricas(ye.iloc[:,j],modelos[obj].predict(xp))['MAE']-base_error)
            importancias.append({'objetivo':obj,'variable':k,'aumento_MAE':float(np.mean(delta)),'desviacion':float(np.std(delta))})
    pd.DataFrame(importancias).to_csv(out/'importancias.csv',index=False)
    dominio={k:{'min':float(x[k].min()) if x[k].notna().any() else None,'max':float(x[k].max()) if x[k].notna().any() else None,
                'valores':sorted(x[k].dropna().unique().tolist()) if x[k].nunique()<=10 else None,'admite_ausencia':bool(x[k].isna().any())} for k in x.columns}
    datos={'entradas':list(x.columns),'objetivos':OBJETIVOS,'dominio':dominio,'modulo_requerido':'modelos_mejorados.py'}
    guardar_modelo(out/'modelo_evaluacion.joblib',{**datos,'modelos':modelos})
    guardar_modelo(out/'modelo_final.joblib',{**datos,'modelos':finales})
    guardar_json(out/'variables_utilizadas.json',datos)
    guardar_json(out/'resumen.json',{'filas':len(df),'familias':int(g.nunique()),'filas_entrenamiento':len(tr),'filas_prueba':len(te),
        'familias_prueba':int(g.iloc[te].nunique()),'semilla':a.semilla,'excel_sha256':hashlib.sha256(origen.read_bytes()).hexdigest(),
        'versiones':{k:importlib.metadata.version(k) for k in ['scikit-learn','numpy','pandas','joblib']},
        'fc_entrenamiento':sorted(xt.fc_kgf_cm2.unique().tolist()),'fc_prueba':sorted(xe.fc_kgf_cm2.unique().tolist()),
        'segundos':time.monotonic()-inicio,'nota':'Selección por CV exclusivamente. Prueba final usada una sola vez para comparar. Modelo final reajustado con toda la base. Mejor entre opciones ensayadas, no garantía de óptimo universal.'})
    shutil.copy2(Path(__file__).with_name('modelos_mejorados.py'),out/'modelos_mejorados.py')
    partes=['<!doctype html><html lang="es"><meta charset="utf-8"><title>Comparación de modelos</title>',
        '<style>body{font:16px Arial;margin:35px;color:#173042}table{border-collapse:collapse;margin-bottom:25px}td,th{padding:9px;border:1px solid #ddd}th{background:#e5edf5}</style>',
        '<h1>Modelo seleccionado con base ampliada</h1>',
        f'<p>{len(df)} estructuras. {len(tr)} para desarrollo y {len(te)} de prueba; ninguna familia compartida. Tres particiones de validación para elegir, sin usar la prueba final.</p>',
        '<h2>Prueba final: seleccionado y Random Forest directo</h2>',
        tabla[tabla.conjunto.isin(['prueba_familias_reservadas','RF_directo_misma_base'])].to_html(index=False,float_format=lambda v:f'{v:.5g}'),
        '<h2>Configuraciones seleccionadas</h2>',pd.DataFrame([{'respuesta':k,'modelos':' + '.join(v)} for k,v in seleccion.items()]).to_html(index=False),
        '<h2>Comparación conjunta en validación: menor es mejor</h2>',pd.DataFrame(scores).sort_values('criterio_conjunto').to_html(index=False,float_format=lambda v:f'{v:.4g}'),
        '<p>Las mejoras se miden contra el RF directo sobre la misma base y prueba. Las importancias no son causales; entradas correlacionadas y permutaciones no físicas afectan su interpretación. No implica cumplimiento normativo. Modelo final entrenado con toda la base; la prueba corresponde al modelo de evaluación.</p>',
        '<h2>Efecto de la cantidad de ejemplos (validación interna fija)</h2>',pd.DataFrame(aprendizaje).to_html(index=False,float_format=lambda v:f'{v:.4g}'),'</html>']
    partes.pop()
    partes.append('<h2>Variables que más utiliza cada modelo</h2><p>Incremento del error absoluto al permutar una entrada. No representa causalidad; variables correlacionadas pueden compartir importancia.</p>')
    importancia_df=pd.DataFrame(importancias)
    for obj in OBJETIVOS:
        top=importancia_df[importancia_df.objetivo==obj].sort_values('aumento_MAE',ascending=False).head(15)
        partes.extend(['<h3>'+html.escape(obj)+'</h3>',top[['variable','aumento_MAE','desviacion']].to_html(index=False,float_format=lambda v:f'{v:.5g}')])
    partes.append('</html>')
    (out/'informe.html').write_text('\n'.join(partes),encoding='utf-8')
    print(tabla[tabla.conjunto=='prueba_familias_reservadas'].to_string(index=False),flush=True)
    print(f'Listo: {out.resolve()}',flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--excel',required=True);p.add_argument('--salida',default='resultados_ml_optimizado')
    p.add_argument('--semilla',type=int,default=48371);a=p.parse_args()
    with threadpool_limits(limits=4): ejecutar(a)

if __name__=='__main__':main()
