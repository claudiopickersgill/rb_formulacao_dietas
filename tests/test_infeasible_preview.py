import unittest
import pandas as pd
from src.solver import solve_least_cost


def ingredients():
    return pd.DataFrame([
        dict(ingredient_id='a',nome='A',tipo='Alimento',preco_kg=1,inclusao_min=0,inclusao_max=100,PB=10,NDT=90,Cu=.001),
        dict(ingredient_id='b',nome='B',tipo='Alimento',preco_kg=2,inclusao_min=0,inclusao_max=100,PB=20,NDT=50,Cu=.003),
    ])


class InfeasiblePreviewTests(unittest.TestCase):
    def test_impossible_protein_shows_achieved_values(self):
        result=solve_least_cost(ingredients(),pd.DataFrame([
            dict(nutriente='PB',minimo=30,maximo=None),
            dict(nutriente='NDT',minimo=None,maximo=None)]))
        self.assertFalse(result.success)
        self.assertEqual(result.status,'inviavel')
        self.assertTrue(result.raw['diagnostic_preview'])
        values=result.constraints.set_index('nutriente')
        self.assertAlmostEqual(values.loc['PB','resultado'],20)
        self.assertAlmostEqual(values.loc['PB','falta_minimo'],10)
        self.assertEqual(values.loc['PB','situacao'],'Fora do limite')
        self.assertAlmostEqual(values.loc['NDT','resultado'],50)
        self.assertAlmostEqual(result.items['inclusao_calculada'].sum(),100)

    def test_inclusion_bounds_are_not_relaxed(self):
        items=ingredients();items.loc[1,'inclusao_max']=50
        result=solve_least_cost(items,pd.DataFrame([dict(nutriente='PB',minimo=30,maximo=None)]))
        self.assertFalse(result.success)
        self.assertLessEqual(result.items.iloc[1]['inclusao_calculada'],50+1e-6)
        self.assertAlmostEqual(result.constraints.iloc[0]['resultado'],15)

    def test_conflicting_nutrients_and_micro_scale(self):
        result=solve_least_cost(ingredients(),pd.DataFrame([
            dict(nutriente='PB',minimo=18,maximo=None),
            dict(nutriente='NDT',minimo=80,maximo=None),
            dict(nutriente='Cu',minimo=None,maximo=.002)]))
        self.assertFalse(result.success)
        self.assertTrue(result.raw['diagnostic_preview'])
        x=result.items['inclusao_calculada'].to_numpy()
        values=result.constraints.set_index('nutriente')
        self.assertAlmostEqual(values.loc['Cu','resultado'],(.001*x[0]+.003*x[1])/100)
        self.assertTrue((values['situacao']=='Fora do limite').any())

    def test_excess_is_reported(self):
        result=solve_least_cost(ingredients(),pd.DataFrame([dict(nutriente='PB',minimo=None,maximo=5)]))
        self.assertAlmostEqual(result.constraints.iloc[0]['resultado'],10)
        self.assertAlmostEqual(result.constraints.iloc[0]['excesso_maximo'],5)

    def test_valid_solution_keeps_original_behavior(self):
        result=solve_least_cost(ingredients(),pd.DataFrame([dict(nutriente='PB',minimo=12,maximo=15)]))
        self.assertTrue(result.success)
        self.assertAlmostEqual(result.cost_per_kg,1.2)
        self.assertNotIn('diagnostic_preview',result.raw)

    def test_invalid_input_has_no_preview(self):
        items=ingredients();items['inclusao_min']=60
        result=solve_least_cost(items,pd.DataFrame([dict(nutriente='PB',minimo=12,maximo=None)]))
        self.assertFalse(result.success)
        self.assertTrue(result.items.empty)
        self.assertFalse(result.raw.get('diagnostic_preview',False))


if __name__=='__main__':
    unittest.main()
