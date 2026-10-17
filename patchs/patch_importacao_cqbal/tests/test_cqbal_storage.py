import copy
import re
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd

from src.config import INGREDIENT_COLUMNS, TABLE_SCHEMAS
from src.repositories.google_sheets import GoogleSheetsRepository
from src.repositories.local import LocalRepository


class Sheet:
    def __init__(self, header):
        self.values=[header[:]]
        self.col_count=len(header)
        self.clears=0

    def get_all_values(self):
        # Simula strings formatadas pt-BR, como o get_all_values real.
        def fmt(v):
            if isinstance(v,bool): return 'TRUE' if v else 'FALSE'
            if isinstance(v,float): return str(v).replace('.',',')
            return str(v)
        return [[fmt(v) for v in row] for row in self.values]

    def add_cols(self, n): self.col_count+=n

    def update(self, values, range_name='A1', **kwargs):
        row=int(re.search(r'\d+',range_name).group())-1
        for i,value in enumerate(values):
            while len(self.values)<=row+i: self.values.append([])
            self.values[row+i]=list(value)

    def append_row(self, values, **kwargs): self.values.append(list(values))

    def clear(self):
        self.clears+=1
        self.values=[]


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.sheets={name:Sheet(cols) for name,cols in TABLE_SCHEMAS.items()}

    def repository(self):
        repo=GoogleSheetsRepository.__new__(GoogleSheetsRepository)
        repo._cache={}
        repo.cache_ttl_seconds=60
        repo._worksheet=lambda name:self.sheets[name]
        repo._call=lambda operation:operation()
        return repo

    def test_append_cache_update_and_provenance(self):
        a,b=self.repository(),self.repository()
        b.list_ingredients(False)
        first=a.upsert_ingredient(dict(tipo='Alimento',nome='A',ativo=True,MS=90,Cu=.0001,cqbal_dados='{"N":3}'),'admin')
        second=b.upsert_ingredient(dict(tipo='Alimento',nome='B',ativo=True,MS=92),'formulador')
        a.clear_cache()
        self.assertEqual(len(a.list_ingredients()),2)
        first.pop('cqbal_dados')
        first['nome']='A editado'
        a.upsert_ingredient(first,'admin')
        a.clear_cache()
        frame=a.list_ingredients(False)
        self.assertEqual(frame.loc[frame['nome'].eq('A editado'),'cqbal_dados'].iloc[0],'{"N":3}')
        self.assertEqual(self.sheets['ingredientes'].clears,0)
        self.assertEqual(len(self.sheets['auditoria'].values),4)
        b.set_ingredient_active(second['ingredient_id'],False,'formulador')
        b.clear_cache()
        self.assertEqual(len(b.list_ingredients()),1)

    def test_schema_append_keeps_existing_cells(self):
        sheet=self.sheets['ingredientes']
        sheet.values=[['ingredient_id','nome','MS'],['a','Existente','90,1']]
        sheet.col_count=3
        before=copy.deepcopy(sheet.values[1:])
        self.repository()._ensure_table('ingredientes',INGREDIENT_COLUMNS)
        self.assertEqual(sheet.values[1:],before)
        self.assertEqual(sheet.values[0][:3],['ingredient_id','nome','MS'])
        self.assertIn('cqbal_dados',sheet.values[0])
        self.assertEqual(sheet.clears,0)

    def test_preserve_existing_units_local(self):
        with tempfile.TemporaryDirectory() as folder:
            repo=LocalRepository(folder)
            repo.initialize()
            saved=repo.upsert_ingredient(dict(nome='Antigo',tipo='Alimento',ativo=True,Cu=.00207,cqbal_dados='fonte'),'admin')
            saved.pop('cqbal_dados')
            saved['nome']='Editado'
            repo.upsert_ingredient(saved,'admin')
            row=repo.list_ingredients().iloc[0]
            self.assertEqual(float(row['Cu']),.00207)
            self.assertEqual(row['cqbal_dados'],'fonte')

    def test_duplicate_and_reactivate(self):
        repo=self.repository()
        active=repo.upsert_ingredient(dict(tipo='Alimento',nome='A',ativo=True),'admin')
        inactive=repo.upsert_ingredient(dict(tipo='Alimento',nome='A',ativo=False),'formulador')
        with self.assertRaises(ValueError): repo.set_ingredient_active(inactive['ingredient_id'],True,'formulador')
        with self.assertRaises(ValueError): repo.upsert_ingredient(dict(tipo='Alimento',nome='A',ativo=True),'formulador')


if __name__ == '__main__':
    unittest.main()
