import unittest
import copy
import json
from pathlib import Path
import numpy as np
from ml import leer
from optimizar import entradas
from modelos_mejorados import auxiliares,RespuestaRegressor

class Mejorados(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p=Path(__file__).resolve().parents[1]/'base_ml_ampliada'
        cls.df=leer(p/'estructuras.xlsx').iloc[:50]
        cls.x=entradas(cls.df,json.loads((p/'variables_ml.json').read_text(encoding='utf-8')))

    def test_no_lee_resultados(self):
        alterada=self.df.copy()
        for k in ['Tx_s','Ty_s','V_modal_ajustado_X_kgf','deriva_max_X']:
            alterada[k]=999999.
        p=Path(__file__).resolve().parents[1]/'base_ml_ampliada/variables_ml.json'
        otra=entradas(alterada,json.loads(p.read_text(encoding='utf-8')))
        np.testing.assert_allclose(self.x.to_numpy(),otra.to_numpy(),equal_nan=True)

    def test_escalas_sismicas_y_periodo(self):
        _,s=auxiliares(self.x)
        x=self.x.copy();x['Z']*=2
        _,doble=auxiliares(x)
        np.testing.assert_allclose(s['Tx_s'],doble['Tx_s'])
        for k in ['V_modal_ajustado_X_kgf','desplazamiento_techo_max_X_cm','deriva_max_X']:
            np.testing.assert_allclose(2*s[k],doble[k])

    def test_cortante_predicho_respeta_piso_del_generador(self):
        est=RespuestaRegressor('V_modal_ajustado_X_kgf','Boosting_15').fit(self.x,self.df.V_modal_ajustado_X_kgf)
        _,s=auxiliares(self.x)
        self.assertTrue((est.predict(self.x)>=s['V_modal_ajustado_X_kgf']).all())

if __name__=='__main__':unittest.main()
