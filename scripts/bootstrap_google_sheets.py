#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.repositories.google_sheets import GoogleSheetsRepository


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cria as abas do aplicativo, importa ingredientes e configura o administrador."
    )
    parser.add_argument("--credentials", required=True, type=Path, help="JSON da conta de serviço")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--spreadsheet-id")
    target.add_argument("--spreadsheet-url")
    parser.add_argument("--table-prefix", default="rb_")
    parser.add_argument("--legacy-title", default="")
    parser.add_argument("--no-legacy-migration", action="store_true")
    parser.add_argument("--ingredients", type=Path, default=Path("data/seed_ingredientes.csv"))
    parser.add_argument("--admin-email", required=True)
    parser.add_argument("--admin-name", default="Administrador")
    args = parser.parse_args()

    credentials = json.loads(args.credentials.read_text(encoding="utf-8"))
    repository = GoogleSheetsRepository(
        credentials,
        spreadsheet_id=args.spreadsheet_id or "",
        spreadsheet_url=args.spreadsheet_url or "",
        cache_ttl_seconds=0,
        table_prefix=args.table_prefix,
        auto_migrate_legacy=not args.no_legacy_migration,
        legacy_worksheet_title=args.legacy_title,
    )
    repository.initialize()

    summary = repository.legacy_migration_summary
    if summary.get("executed"):
        print(
            f"Migração legada: {summary['rows']} ingredientes copiados de "
            f"'{summary['source']}' ({summary['warnings']} alertas)."
        )

    existing = repository.list_ingredients(active_only=False)
    if existing.empty and args.ingredients.exists():
        seed = pd.read_csv(args.ingredients, encoding="utf-8-sig")
        for _, row in seed.iterrows():
            repository.upsert_ingredient(row.to_dict(), actor=args.admin_email)
        print(f"{len(seed)} ingredientes importados do CSV inicial.")
    else:
        print("A tabela de ingredientes já possui dados; o seed CSV foi ignorado.")

    repository.upsert_user(
        {
            "email": args.admin_email,
            "nome": args.admin_name,
            "perfil": "Administrador",
            "ativo": True,
        },
        actor=args.admin_email,
    )
    print("Administrador configurado.")


if __name__ == "__main__":
    main()
