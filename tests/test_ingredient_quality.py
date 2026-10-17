import unittest
import tempfile
import pandas as pd
from src.ingredient_quality import classify_ingredient_notes, active_quality_warnings, IMPORT_NOTE
from src.repositories.local import LocalRepository

class QualityTests(unittest.TestCase):
    def test_classification_is_conservative_and_idempotent(self):
        rows = pd.DataFrame([
            dict(ingredient_id="a", tipo="Mineral", nome="Sal", ativo="TRUE", qualidade_dados="Nome duplicado na planilha legada"),
            dict(ingredient_id="b", tipo="Mineral", nome="Sal", ativo=False, qualidade_dados="Duplicata desativada na migração; mantida para preservar o ID histórico. Registro ativo equivalente: linha 2."),
            dict(ingredient_id="c", tipo="Mineral", nome="Produto", ativo=True, qualidade_dados=IMPORT_NOTE, created_by="migracao_etapa2"),
            dict(ingredient_id="d", tipo="Mineral", nome="Parcial", ativo=True, qualidade_dados="Composição parcial"),
            dict(ingredient_id="e", tipo="Mineral", nome="Revisar", ativo=True, qualidade_dados="Novo alerta"),
        ])
        result = classify_ingredient_notes(rows)
        self.assertEqual(len(active_quality_warnings(result)), 2)
        self.assertEqual(result["observacoes"].str.strip().ne("").sum(), 3)
        pd.testing.assert_frame_equal(result, classify_ingredient_notes(result))
        rows.loc[1, "ativo"] = True
        self.assertIn("a", active_quality_warnings(rows)["ingredient_id"].tolist())

    def test_duplicate_edit_and_reactivation(self):
        with tempfile.TemporaryDirectory() as folder:
            repository = LocalRepository(folder)
            repository.initialize()
            active = repository.upsert_ingredient(dict(tipo="Mineral", nome="Sal", ativo=True, observacoes="Histórico"), "teste")
            inactive = repository.upsert_ingredient(dict(tipo="Mineral", nome="Sal", ativo=False), "teste")
            active.pop("observacoes")
            repository.upsert_ingredient(active, "teste")
            self.assertEqual(repository.list_ingredients().iloc[0]["observacoes"], "Histórico")
            with self.assertRaises(ValueError):
                repository.set_ingredient_active(inactive["ingredient_id"], True, "teste")
            with self.assertRaises(ValueError):
                repository.upsert_ingredient(dict(tipo="Mineral", nome="SAL", ativo=True), "teste")
            repository.set_ingredient_active(active["ingredient_id"], False, "teste")
            repository.set_ingredient_active(inactive["ingredient_id"], True, "teste")
            self.assertEqual(len(repository.list_ingredients()), 1)

if __name__ == "__main__":
    unittest.main()
