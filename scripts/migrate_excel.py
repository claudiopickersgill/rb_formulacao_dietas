#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
HEADERS = [
    "tipo", "nome", "classificacao", "formula_quimica", "fonte", "preco_padrao",
    "MS", "NDT", "PB", "FDN", "FDA", "AMIDO", "CA", "P", "Mg", "Na", "K", "Cl", "S",
    "Fe", "Cu", "Mn", "Zn", "Co", "I", "Se",
]


def column_number(column: str) -> int:
    value = 0
    for char in column:
        value = value * 26 + ord(char) - 64
    return value


def read_sheet(path: Path, sheet_xml: str = "xl/worksheets/sheet5.xml") -> list[list[object]]:
    with ZipFile(path) as archive:
        strings = []
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        for item in root.findall(NS + "si"):
            text = item.find(NS + "t")
            if text is not None:
                strings.append(text.text or "")
            else:
                strings.append("".join((node.text or "") for node in item.findall(".//" + NS + "t")))

        root = ET.fromstring(archive.read(sheet_xml))
        rows: list[list[object]] = []
        for row in root.findall(".//" + NS + "row"):
            values: dict[int, object] = {}
            for cell in row.findall(NS + "c"):
                reference = cell.attrib["r"]
                column = re.match(r"[A-Z]+", reference).group(0)
                index = column_number(column) - 1
                cell_type = cell.attrib.get("t")
                value_node = cell.find(NS + "v")
                value: object = ""
                if cell_type == "inlineStr":
                    text_node = cell.find(".//" + NS + "t")
                    value = text_node.text if text_node is not None else ""
                elif value_node is not None:
                    raw = value_node.text or ""
                    if cell_type == "s":
                        value = strings[int(raw)]
                    elif cell_type == "b":
                        value = raw == "1"
                    else:
                        try:
                            number = float(raw)
                            value = int(number) if number.is_integer() else number
                        except ValueError:
                            value = raw
                values[index] = value
            if values:
                row_values = [""] * (max(values) + 1)
                for index, value in values.items():
                    row_values[index] = value
                rows.append((row_values + [""] * 26)[:26])
        return rows


def migrate(input_path: Path, output_path: Path) -> pd.DataFrame:
    rows = read_sheet(input_path)
    frame = pd.DataFrame(rows[1:], columns=HEADERS)
    frame = frame[
        frame["tipo"].fillna("").astype(str).str.strip().ne("")
        & frame["nome"].fillna("").astype(str).str.strip().ne("")
    ].copy().reset_index(drop=True)

    duplicate_counts = Counter(
        (str(row.tipo).strip().lower(), str(row.nome).strip().lower())
        for row in frame.itertuples()
    )
    quality: list[str] = []
    for row in frame.itertuples():
        issues = []
        key = (str(row.tipo).strip().lower(), str(row.nome).strip().lower())
        if duplicate_counts[key] > 1:
            issues.append("Nome duplicado na planilha original")
        classification = str(row.classificacao or "").strip()
        if len(classification) == 1 and classification.isalpha():
            issues.append("Classificação parece ser nota de rodapé")
        if str(row.tipo).strip().lower() == "mineral" and classification.lower() in {"energético", "energetico"}:
            issues.append("Classificação incompatível com tipo mineral")
        if str(row.tipo).strip().lower() == "alimento":
            major = [row.NDT, row.PB, row.FDN, row.FDA, row.AMIDO]
            numeric = [float(value or 0) for value in major]
            if all(value == 0 for value in numeric):
                issues.append("Composição principal possivelmente incompleta")
            elif float(row.NDT or 0) == 0 and any(value > 0 for value in numeric[2:]):
                issues.append("NDT igual a zero; revisar se é dado ausente")
        quality.append("; ".join(issues))

    frame.insert(0, "ingredient_id", [f"ing_excel_{index + 2:03d}" for index in range(len(frame))])
    frame["ativo"] = True
    frame["qualidade_dados"] = quality
    frame["created_by"] = "migracao_excel"
    frame["created_at"] = ""
    frame["updated_at"] = ""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, encoding="utf-8-sig")
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description="Extrai a tabela de ingredientes do XLSM sem executar macros.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "seed_ingredientes.csv")
    args = parser.parse_args()
    frame = migrate(args.input, args.output)
    print(f"{len(frame)} ingredientes gravados em {args.output}")
    warnings = int(frame["qualidade_dados"].astype(str).str.strip().ne("").sum())
    print(f"{warnings} registros receberam alertas de qualidade.")


if __name__ == "__main__":
    main()
