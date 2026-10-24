"""Estimadores transportables. Sólo usan geometría, materiales, masas y sitio.

Las fórmulas auxiliares son aproximaciones para ML bajo las hipótesis del
generador, no un análisis estructural alternativo ni verificación normativa.
"""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from threadpoolctl import threadpool_limits

def coeficiente(t,tp,tl,dinamico=True):
    t=np.maximum(t,1e-8)
    c=np.where(t<=tp,2.5,np.where(t<=tl,2.5*tp/t,2.5*tp*tl/t**2))
    return np.where(t<.2*tp,1+7.5*t/tp,c) if dinamico else c

def auxiliares(x):
    """Calcula características y escalas sin leer ninguna columna de resultados."""
    z=x.copy();n=x['pisos'].to_numpy();nx=x['vanos_X'].to_numpy();ny=x['vanos_Y'].to_numpy()
    E=4700*np.sqrt(x.fc_kgf_cm2.to_numpy()*.0980665)/.0980665
    H=x.altura_total_cm.to_numpy(); W=x.peso_sismico_kgf.to_numpy()
    zus=(x.Z*x.U*x.S).to_numpy();tp=x.TP_s.to_numpy();tl=x.TL_s.to_numpy()
    z['aux_ZUS']=zus;z['aux_peso_por_area']=W/(x.Lx_cm*x.Ly_cm)
    z['aux_aspecto']=x.Lx_cm/x.Ly_cm;z['aux_E']=E
    tstatic=H/3500
    vmin=.8*W*zus*np.maximum(coeficiente(tstatic,tp,tl,False)/8,.11)
    z['aux_cortante_minimo']=vmin
    escalas={}
    grupos={'esquina':4,'exterior':2*(nx-1)+2*(ny-1),'interior':(nx-1)*(ny-1)}
    for eje in ('X','Y'):
        energia=np.zeros(len(x));masa_modal=np.zeros(len(x));elev=np.zeros(len(x));prev=np.zeros(len(x))
        for k in range(1,6):
            activo=n>=k;h=x[f'piso{k}_altura_cm'].fillna(1).to_numpy()
            segundo=(x.piso_inicio_bloque2.fillna(99).to_numpy()<=k)
            sumaI=np.zeros(len(x));sumaA=np.zeros(len(x))
            for g,cantidad in grupos.items():
                bx=np.where(segundo,x[f'col_{g}_bloque2_bX_cm'].fillna(x[f'col_{g}_bloque1_bX_cm']),x[f'col_{g}_bloque1_bX_cm'])
                by=np.where(segundo,x[f'col_{g}_bloque2_bY_cm'].fillna(x[f'col_{g}_bloque1_bY_cm']),x[f'col_{g}_bloque1_bY_cm'])
                sumaI+=cantidad*(by*bx**3 if eje=='X' else bx*by**3)/12
                sumaA+=cantidad*bx*by
            bv=np.where(segundo,x[f'viga_{eje}_bloque2_base_cm'].fillna(x[f'viga_{eje}_bloque1_base_cm']),x[f'viga_{eje}_bloque1_base_cm'])
            hv=np.where(segundo,x[f'viga_{eje}_bloque2_peralte_cm'].fillna(x[f'viga_{eje}_bloque1_peralte_cm']),x[f'viga_{eje}_bloque1_peralte_cm'])
            Iv=bv*hv**3/12
            luz=x[f'luz_media_{eje}_cm'].to_numpy()
            rho=(Iv/luz)/(sumaI/((nx+1)*(ny+1))/h)
            rigidez=12*E*sumaI/h**3*(rho/(rho+2))
            elev+=np.where(activo,h,0);phi=elev/H
            energia+=np.where(activo,rigidez*(phi-prev)**2,0)
            masa=x[f'piso{k}_peso_sismico_kgf'].fillna(0).to_numpy()/980.665
            masa_modal+=masa*phi**2;prev=phi
            z[f'aux_K_{eje}_{k}']=np.where(activo,rigidez,np.nan)
            if k==1: z[f'aux_esbeltez_{eje}']=H/np.sqrt(sumaI/sumaA)
        T=2*np.pi*np.sqrt(masa_modal/energia)
        C=coeficiente(T,tp,tl)
        U=.75*zus*980.665*C*(T/(2*np.pi))**2
        z[f'aux_T_{eje}']=T;z[f'aux_T_TP_{eje}']=T/tp;z[f'aux_C_{eje}']=C
        z[f'aux_u_{eje}']=U;z[f'aux_deriva_{eje}']=U/H
        escalas['Tx_s' if eje=='X' else 'Ty_s']=T
        escalas[f'V_modal_ajustado_{eje}_kgf']=vmin
        escalas[f'desplazamiento_techo_max_{eje}_cm']=U
        escalas[f'deriva_max_{eje}']=U/H
    return z,escalas

CONFIGURACIONES={
    'RF_original':dict(tipo='rf',fisica=False,normalizar=False,arboles=200,hoja=2,fraccion=.8),
    'RF_fisica':dict(tipo='rf',fisica=True,normalizar=False,arboles=250,hoja=1,fraccion=1.),
    'RF_normalizado':dict(tipo='rf',fisica=True,normalizar=True,arboles=250,hoja=1,fraccion=.8),
    'ExtraTrees_1':dict(tipo='et',fisica=True,normalizar=True,arboles=300,hoja=1,fraccion=1.),
    'ExtraTrees_2':dict(tipo='et',fisica=True,normalizar=True,arboles=300,hoja=2,fraccion=.8),
    'Boosting_15':dict(tipo='hgb',fisica=True,normalizar=True,iteraciones=350,hoja=10,nodos=15,lr=.06),
    'Boosting_31':dict(tipo='hgb',fisica=True,normalizar=True,iteraciones=450,hoja=15,nodos=31,lr=.05),
}

class RespuestaRegressor(RegressorMixin,BaseEstimator):
    def __init__(self,objetivo,configuracion='RF_normalizado',semilla=42):
        self.objetivo=objetivo;self.configuracion=configuracion;self.semilla=semilla

    def fit(self,X,y):
        c=CONFIGURACIONES[self.configuracion]
        self.feature_names_in_=np.array(X.columns,dtype=object);self.n_features_in_=X.shape[1]
        features,scales=auxiliares(X) if c['fisica'] else (X,None)
        valores=np.log(np.asarray(y)/scales[self.objetivo]) if c['normalizar'] else np.asarray(y)
        if c['tipo'] in ('rf','et'):
            clase=RandomForestRegressor if c['tipo']=='rf' else ExtraTreesRegressor
            est=clase(n_estimators=c['arboles'],min_samples_leaf=c['hoja'],max_features=c['fraccion'],random_state=self.semilla,n_jobs=4)
        else:
            est=HistGradientBoostingRegressor(max_iter=c['iteraciones'],max_leaf_nodes=c['nodos'],
                min_samples_leaf=c['hoja'],learning_rate=c['lr'],l2_regularization=.1,
                early_stopping=False,random_state=self.semilla)
        self.modelo_=make_pipeline(SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True),est)
        self.modelo_.fit(features,valores)
        return self

    def predict(self,X):
        c=CONFIGURACIONES[self.configuracion]
        features,scales=auxiliares(X) if c['fisica'] else (X,None)
        # Evitar sobrecarga de OpenMP al consultar una sola estructura.
        with threadpool_limits(limits=4):
            pred=self.modelo_.predict(features)
        if c['normalizar']: pred=np.exp(np.clip(pred,-20,20))*scales[self.objetivo]
        if c['fisica'] and self.objetivo.startswith('V_modal_ajustado'): pred=np.maximum(pred,scales[self.objetivo])
        return np.maximum(pred,1e-12)

class PromedioModelos(RegressorMixin,BaseEstimator):
    def __init__(self,modelos): self.modelos=modelos
    def predict(self,X): return np.mean([m.predict(X) for m in self.modelos],axis=0)
