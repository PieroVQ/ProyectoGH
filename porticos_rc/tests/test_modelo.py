import json
from pathlib import Path
import copy
import numpy as np
import openseespy.opensees as ops
from porticos.normas import *
from porticos.geometria import generar_familia,ajustar_losas,metrar
from porticos.generador import preparar
from porticos.analisis import analizar,condensar,matriz_masa,modos
from porticos.datos import a_fila,desde_fila,exportar,leer_filas

def config(): return json.loads((Path(__file__).parents[1]/'config.json').read_text())

def modelo():
    c=config(); b=generar_familia(c,1)
    b.update(n=2,lx=[400.,400.],ly=[400.,400.],alturas=[300.,300.],transicion=0,ratio_col=1.)
    b['columnas']=[{g:[45.,45.] for g in ('esquina','exterior','interior')}]
    b['vigas']=[{'X':[25.,50.],'Y':[25.,50.]}];b['paños']=[[1,1],[1,1]]
    ajustar_losas(b);return preparar(b,c)

def test_espectro_ramas_y_unidades():
    assert G==980.665
    assert np.allclose(factor_c([0,.12,.6,2.,4.],.6,2.),[1,2.5,2.5,.75,.1875])
    assert factor_c(0,.6,2.,True)==2.5
    assert sitio(.45,'S3')==(1.2,.9,1.6)

def test_cqc_modos_repetidos_y_separados():
    rho=correlacion_cqc([1.,1.])
    assert np.allclose(rho,1)
    assert np.isclose(cqc(np.array([2.,3.]),rho),5.)
    assert correlacion_cqc([1.,100.])[0,1]<.001
    assert np.isclose(combinar_direcciones(10,10),np.sqrt(109))

def test_simetria_equilibrio_y_masa():
    b=modelo();a=analizar(b)
    assert a['error_equilibrio']<1e-9
    assert np.isclose(a['Tx'],a['Ty'],rtol=1e-6)
    assert np.allclose(a['masa_modal'].sum(axis=1),1,atol=1e-8)
    assert np.allclose(a['metrado']['cm'],400)
    assert np.allclose(a['deriva_normativa'][:,0].max(axis=1),a['deriva_normativa'][:,1].max(axis=1),rtol=1e-6)

def test_modos_condensados_contra_opensees():
    b=modelo();m=metrar(b);K,*_=condensar(b,m)
    w,T,phi,_=modos(K,matriz_masa(m))
    ev=np.array(ops.eigen('-fullGenLapack',3*b['n']))
    assert np.allclose(w*w,ev,rtol=1e-5)
    # Escalar la masa por cuatro duplica los períodos.
    _,t2,_,_=modos(K,matriz_masa(m)*4)
    assert np.allclose(t2,2*T)

def test_reconstruccion_excel_una_hoja(tmp_path):
    b=modelo();a=analizar(b);r=a_fila(b,a,1)
    path=tmp_path/'base.xlsx';exportar([r],path)
    back=leer_filas(path);assert len(back)==1
    assert all(not isinstance(v,(list,dict,tuple)) for v in back[0].values())
    b2=desde_fila(back[0]);a2=analizar(b2)
    assert np.isclose(a2['Tx'],a['Tx'],rtol=1e-10)
    assert np.allclose(a2['deriva_normativa'],a['deriva_normativa'])
    assert back[0]['piso5_altura_cm'] is None

def test_cantilever_independiente():
    # Solución cerrada PL^3/(3EI), además de comprobar orientación espacial.
    ops.wipe();ops.model('basic','-ndm',3,'-ndf',6)
    ops.node(1,0,0,0);ops.node(2,0,0,300);ops.fix(1,1,1,1,1,1,1)
    E=250000.;I=40**4/12
    ops.geomTransf('Linear',1,1,0,0)
    ops.element('elasticBeamColumn',1,1,2,1600,E,E/2.4,1e5,I,I,1)
    ops.timeSeries('Constant',1);ops.pattern('Plain',1,1);ops.load(2,1000,0,0,0,0,0)
    ops.constraints('Plain');ops.numberer('Plain');ops.system('BandGeneral');ops.algorithm('Linear');ops.integrator('LoadControl',1);ops.analysis('Static')
    assert ops.analyze(1)==0
    assert np.isclose(ops.nodeDisp(2,1),1000*300**3/(3*E*I))

def test_intercambio_de_ejes_y_asimetria():
    b=modelo();b['lx']=[350.,500.];b['ly']=[450.,400.]
    b['paños']=[[1,0],[0,0]]
    ajustar_losas(b);b=preparar(b,config());a=analizar(b)
    z=copy.deepcopy(b);z['lx'],z['ly']=b['ly'],b['lx']
    z['paños']=np.array(b['paños']).T.tolist()
    for block in z['columnas']:
        for g in block: block[g]=block[g][::-1]
    for block in z['vigas']: block['X'],block['Y']=block['Y'],block['X']
    az=analizar(z)
    assert np.isclose(a['Tx'],az['Ty'],rtol=1e-6)
    assert np.isclose(a['Ty'],az['Tx'],rtol=1e-6)
    assert np.isclose(a['deriva_normativa'][:,0,:4].max(),az['deriva_normativa'][:,1,:4].max(),rtol=1e-6)

def test_reanudar_sin_duplicar_y_con_familia_parcial(tmp_path):
    from porticos.generador import ejecutar
    c=config();c['cantidad']=2
    ejecutar(c,tmp_path/'resumed')
    c['cantidad']=4;ejecutar(c,tmp_path/'resumed',True)
    ejecutar(c,tmp_path/'fresh')
    resumed=leer_filas(tmp_path/'resumed/estructuras.xlsx');fresh=leer_filas(tmp_path/'fresh/estructuras.xlsx')
    assert resumed==fresh

def test_deriva_modal_no_resta_de_envolventes():
    rho=np.eye(2)
    floor1=np.array([1.,1.]);floor2=np.array([2.,-1.])
    correct=cqc(floor2-floor1,rho)
    wrong=cqc(floor2,rho)-cqc(floor1,rho)
    assert not np.isclose(correct,wrong)

def test_resistencias_variables():
    from porticos.geometria import validar_config
    c=config(); validar_config(c)
    valores={generar_familia(c,i)['fc'] for i in range(1,41)}
    assert valores=={210.,280.}
    c['fc_kgf_cm2']=280.
    assert generar_familia(c,1)['fc']==280.
    b=modelo(); b['fc']=210.; a=analizar(b)
    b2=copy.deepcopy(b); b2['fc']=280.; a2=analizar(b2)
    assert a['Tx']>a2['Tx']
    assert not a_fila(b,a,1)['fc_alcanza_21MPa']
    assert a_fila(b2,a2,2)['fc_alcanza_21MPa']
