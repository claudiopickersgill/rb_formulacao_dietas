#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path, nargs="?", default=Path("data/seed_ingredientes.csv"))
    args = parser.parse_args()
    frame = pd.read_csv(args.csv, encoding="utf-8-sig")
    warnings = frame[frame["qualidade_dados"].fillna("").astype(str).str.strip().ne("")]
    print(f"Registros: {len(frame)}")
    print(f"Com alerta: {len(warnings)}")
    print(warnings[["ingredient_id", "tipo", "nome", "qualidade_dados"]].to_string(index=False))


if __name__ == "__main__":
    main()
