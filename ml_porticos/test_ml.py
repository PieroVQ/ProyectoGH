import unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
import pandas as pd
import tempfile
from pathlib import Path
from zipfile import ZipFile
from ml import separar, modelo, numericos, predecir, metricas

class PruebasML(unittest.TestCase):
    def test_familias_no_se_mezclan(self):
        grupos=pd.Series(np.repeat(np.arange(20),3))
        tr,te=separar(grupos,42)
        self.assertFalse(set(grupos.iloc[tr]) & set(grupos.iloc[te]))
        self.assertEqual(len(tr)+len(te),len(grupos))

    def test_imputacion_aprende_solo_entrenamiento(self):
        x=pd.DataFrame({'a':[1.,3.,np.nan],'b':[np.nan]*3})
        m=modelo(10,42).fit(x,[1.,2.,3.])
        self.assertEqual(m[0].statistics_[0],2.)
        p=m.predict(pd.DataFrame({'a':[1000.],'b':[np.nan]}))
        self.assertTrue(np.isfinite(p).all())
        self.assertEqual(m[0].statistics_[0],2.)

    def test_rechaza_resistencia_no_entrenada(self):
        paquete={'entradas':['fc_kgf_cm2'],'dominio':{'fc_kgf_cm2':{
            'min':210.,'max':280.,'valores':[210.,280.],'admite_ausencia':False}}}
        with patch('ml.joblib.load',return_value=paquete),patch('ml.leer',return_value=pd.DataFrame({'fc_kgf_cm2':[250.]})):
            with self.assertRaisesRegex(ValueError,'valor no entrenado'):
                predecir(SimpleNamespace(modelo='modelo',excel='datos',salida='nunca.csv'))

    def test_no_acepta_infinitos(self):
        with self.assertRaises(ValueError): numericos(pd.DataFrame({'x':[np.inf]}),['x'])

    def test_metricas(self):
        self.assertEqual(metricas([1,2,3],[1,2,3]),{'MAE':0.,'RMSE':0.,'R2':1.})

    def test_orden_vanos_no_se_pierde(self):
        from ml import VANOS_ORDENADOS,validar_vanos
        df=pd.DataFrame({'vanos_X':[3,3],'vanos_Y':[2,2],'Lx_cm':[1200,1200],'Ly_cm':[800,800],
                         'luz_X_1_cm':[300,300],'luz_X_2_cm':[600,300],'luz_X_3_cm':[300,600],
                         'luz_Y_1_cm':[400,400],'luz_Y_2_cm':[400,400]})
        for k in VANOS_ORDENADOS:
            if k not in df: df[k]=np.nan
        validar_vanos(df)
        self.assertFalse(df[VANOS_ORDENADOS].iloc[0].equals(df[VANOS_ORDENADOS].iloc[1]))
        df.loc[0,'luz_X_3_cm']=400
        with self.assertRaises(ValueError): validar_vanos(df)

    def test_publicacion_y_respaldo(self):
        from actualizar import publicar
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); s=p/'salida'; t=p/'temporal'; s.mkdir();t.mkdir()
            (s/'a').write_text('anterior');(s/'personal').write_text('conservar');(t/'a').write_text('nuevo')
            respaldo=publicar(t,s,['a'])
            self.assertEqual((s/'a').read_text(),'nuevo')
            self.assertEqual((s/'personal').read_text(),'conservar')
            with ZipFile(respaldo) as z: self.assertEqual(z.read('a'),b'anterior')

    def test_publicacion_fallida_restaura(self):
        import actualizar
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);s=p/'salida';t=p/'temporal';s.mkdir();t.mkdir()
            for n in ['a','b']:
                (s/n).write_text('anterior');(t/n).write_text('nuevo')
            real=actualizar.reemplazar
            def fallo(origen,destino):
                if Path(origen).name=='publicar_b': raise PermissionError('Bloqueado')
                real(origen,destino)
            with patch('actualizar.reemplazar',side_effect=fallo):
                with self.assertRaises(PermissionError): actualizar.publicar(t,s,['a','b'])
            self.assertEqual((s/'a').read_text(),'anterior');self.assertEqual((s/'b').read_text(),'anterior')
            self.assertEqual((t/'a').read_text(),'nuevo');self.assertEqual((t/'b').read_text(),'nuevo')

if __name__=='__main__': unittest.main()
