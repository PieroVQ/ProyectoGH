"""Diagnóstico posterior a la selección: no vuelve a seleccionar modelos."""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd
from ml import OBJETIVOS,leer,metricas

def auditar(excel,carpeta):
    carpeta=Path(carpeta);df=leer(excel)
    p=pd.read_csv(carpeta/'predicciones_prueba.csv').merge(df[['ID_estructura','pisos','fc_kgf_cm2','Z']],on='ID_estructura',validate='one_to_one')
    resultados=[];intervalos=[];rng=np.random.default_rng(491)
    for obj in OBJETIVOS:
        for columna in ['pisos','fc_kgf_cm2','Z']:
            for valor,sub in p.groupby(columna):
                real=sub[obj+'_real'];pred=sub[obj+'_predicho']
                resultados.append({'objetivo':obj,'grupo':columna,'valor':valor,'casos':len(sub),**metricas(real,pred),
                    'error_relativo_p90_pct':float(np.quantile(abs(pred-real)/real*100,.9))})
        # Re-muestreo por familia: en la base nueva hay una estructura por familia.
        grupos=list(p.groupby('ID_familia').indices.values());valores=[]
        for _ in range(300):
            indices=np.concatenate([grupos[i] for i in rng.integers(0,len(grupos),len(grupos))])
            sub=p.iloc[indices];valores.append(metricas(sub[obj+'_real'],sub[obj+'_predicho'])['R2'])
        intervalos.append({'objetivo':obj,'R2_p025':float(np.quantile(valores,.025)),'R2_p975':float(np.quantile(valores,.975)),
                          'nota':'Intervalo descriptivo bootstrap por familias, 300 réplicas. No garantía fuera del dominio.'})
    pd.DataFrame(resultados).to_csv(carpeta/'metricas_por_grupo.csv',index=False)
    pd.DataFrame(intervalos).to_csv(carpeta/'intervalos_R2.csv',index=False)
    return intervalos

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--excel',required=True);p.add_argument('--modelos',required=True)
    a=p.parse_args();auditar(a.excel,a.modelos)
