#!/usr/bin/env python3
from __future__ import annotations

import importlib
import sys
import tempfile
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def check_dependencies() -> bool:
    packages = ["streamlit", "pandas", "numpy", "scipy", "gspread", "reportlab", "xlsxwriter"]
    ok = True
    for package in packages:
        try:
            module = importlib.import_module(package)
            print(f"[OK] {package}: {getattr(module, '__version__', 'instalado')}")
        except Exception as exc:
            ok = False
            print(f"[ERRO] {package}: {exc}")
    return ok


def check_core() -> bool:
    from src.exports import make_excel_bytes, make_pdf_bytes
    from src.repositories.local import LocalRepository
    from src.solver import solve_least_cost

    with tempfile.TemporaryDirectory() as temporary:
        repository = LocalRepository(temporary, PROJECT_ROOT / "data")
        repository.initialize()
        count = len(repository.list_ingredients(active_only=False))
        if count != 82:
            print(f"[ERRO] Base inicial: esperados 82 ingredientes, encontrados {count}.")
            return False
        print("[OK] Base inicial: 82 ingredientes.")

    items = pd.DataFrame(
        [
            {"ingredient_id": "a", "nome": "A", "preco_kg": 1, "inclusao_min": 0, "inclusao_max": 100, "PB": 8},
            {"ingredient_id": "b", "nome": "B", "preco_kg": 2, "inclusao_min": 0, "inclusao_max": 100, "PB": 20},
        ]
    )
    restrictions = pd.DataFrame([{"nutriente": "PB", "minimo": 12, "maximo": 15}])
    result = solve_least_cost(items, restrictions)
    if not result.success:
        print(f"[ERRO] Solver: {result.message}")
        return False
    print(f"[OK] Solver: custo ótimo R$ {result.cost_per_kg:.4f}/kg.")

    metadata = {"nome": "Teste", "proprietario": "setup", "status": "Ótima", "custo_kg": result.cost_per_kg}
    if not make_excel_bytes(metadata, result.items, result.constraints).startswith(b"PK"):
        print("[ERRO] Exportação Excel.")
        return False
    if not make_pdf_bytes(metadata, result.items, result.constraints).startswith(b"%PDF"):
        print("[ERRO] Exportação PDF.")
        return False
    print("[OK] Exportações Excel e PDF.")
    return True


def main() -> int:
    dependencies_ok = check_dependencies()
    core_ok = check_core()
    if dependencies_ok and core_ok:
        print("\nAmbiente pronto para executar: streamlit run app.py")
        return 0
    print("\nCorrija os itens acima antes de executar o aplicativo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
