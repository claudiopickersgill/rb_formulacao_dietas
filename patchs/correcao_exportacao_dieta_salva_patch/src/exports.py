from __future__ import annotations

from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .config import NUTRIENT_CODES
from .diet_loading import normalize_loaded_constraints, normalize_loaded_items, normalize_loaded_metadata
from .utils import as_float, format_brl, safe_filename


def _display_items(items: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "nome",
        "tipo",
        "classificacao",
        "preco_kg",
        "inclusao_min",
        "inclusao_max",
        "inclusao_calculada",
        "custo_parcial",
    ]
    existing = [c for c in columns if c in items.columns]
    return items[existing].copy()


def make_csv_bytes(items: pd.DataFrame) -> bytes:
    normalized_items = normalize_loaded_items(items)
    return _display_items(normalized_items).to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


def make_excel_bytes(metadata: dict, items: pd.DataFrame, constraints: pd.DataFrame) -> bytes:
    metadata = normalize_loaded_metadata(metadata)
    items = normalize_loaded_items(items)
    constraints = normalize_loaded_constraints(constraints)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        title_fmt = workbook.add_format(
            {"bold": True, "font_size": 16, "font_color": "#17365D", "bottom": 2}
        )
        header_fmt = workbook.add_format(
            {"bold": True, "bg_color": "#D9EAF7", "border": 1, "align": "center"}
        )
        money_fmt = workbook.add_format({"num_format": 'R$ #,##0.0000', "border": 1})
        number_fmt = workbook.add_format({"num_format": "0.0000", "border": 1})
        text_fmt = workbook.add_format({"border": 1})

        summary = pd.DataFrame(
            [
                ["Nome", metadata.get("nome", "")],
                ["Descrição", metadata.get("descricao", "")],
                ["Categoria animal", metadata.get("categoria_animal", "")],
                ["Base", metadata.get("base", "Matéria seca")],
                ["Objetivo", metadata.get("objetivo", "Custo mínimo")],
                ["Autor", metadata.get("proprietario", "")],
                ["Status", metadata.get("status", "")],
                ["Custo por kg", metadata.get("custo_kg", metadata.get("custo_per_kg"))],
            ],
            columns=["Campo", "Valor"],
        )
        summary.to_excel(writer, sheet_name="Resumo", index=False, startrow=2)
        ws = writer.sheets["Resumo"]
        ws.write("A1", "Relatório de formulação", title_fmt)
        ws.set_column("A:A", 24)
        ws.set_column("B:B", 52)
        ws.set_row(2, None, header_fmt)
        ws.write_number(10, 1, as_float(metadata.get("custo_kg", metadata.get("custo_per_kg")), 0.0) or 0.0, money_fmt)

        display_items = _display_items(items)
        display_items.to_excel(writer, sheet_name="Ingredientes", index=False)
        wi = writer.sheets["Ingredientes"]
        wi.freeze_panes(1, 0)
        wi.autofilter(0, 0, max(len(display_items), 1), max(len(display_items.columns) - 1, 0))
        for col, name in enumerate(display_items.columns):
            wi.write(0, col, name, header_fmt)
            width = 32 if name in {"nome", "classificacao"} else 16
            cell_fmt = money_fmt if name in {"preco_kg", "custo_parcial"} else number_fmt
            if name in {"nome", "tipo", "classificacao"}:
                cell_fmt = text_fmt
            wi.set_column(col, col, width, cell_fmt)

        constraints.to_excel(writer, sheet_name="Nutrientes", index=False)
        wn = writer.sheets["Nutrientes"]
        wn.freeze_panes(1, 0)
        for col, name in enumerate(constraints.columns):
            wn.write(0, col, name, header_fmt)
            wn.set_column(col, col, 23 if name in {"descricao", "situacao"} else 14, text_fmt if name in {"nutriente", "descricao", "unidade", "situacao"} else number_fmt)

        nutrient_cols = [c for c in NUTRIENT_CODES if c in items.columns]
        if nutrient_cols:
            composition = items[["nome", *nutrient_cols]].copy()
            composition.to_excel(writer, sheet_name="Composição utilizada", index=False)
            wc = writer.sheets["Composição utilizada"]
            wc.freeze_panes(1, 1)
            wc.set_column(0, 0, 32)
            wc.set_column(1, len(composition.columns) - 1, 12, number_fmt)
            for col, name in enumerate(composition.columns):
                wc.write(0, col, name, header_fmt)

    return output.getvalue()


def make_pdf_bytes(metadata: dict, items: pd.DataFrame, constraints: pd.DataFrame) -> bytes:
    metadata = normalize_loaded_metadata(metadata)
    items = normalize_loaded_items(items)
    constraints = normalize_loaded_constraints(constraints)
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"Formulação - {metadata.get('nome', '')}",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CenteredTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17365D"),
        )
    )
    story = [Paragraph("Relatório de formulação de dieta", styles["CenteredTitle"]), Spacer(1, 5 * mm)]
    summary_data = [
        ["Dieta", metadata.get("nome", ""), "Autor", metadata.get("proprietario", "")],
        ["Categoria", metadata.get("categoria_animal", ""), "Base", metadata.get("base", "Matéria seca")],
        ["Status", metadata.get("status", ""), "Custo/kg", format_brl(metadata.get("custo_kg", metadata.get("custo_per_kg")), 4)],
    ]
    summary_table = Table(summary_data, colWidths=[28 * mm, 82 * mm, 28 * mm, 82 * mm])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#D9EAF7")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#D9EAF7")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.extend([summary_table, Spacer(1, 5 * mm), Paragraph("Ingredientes", styles["Heading2"])])

    item_headers = ["Ingrediente", "Preço/kg", "Mín.", "Máx.", "Inclusão", "Custo parcial"]
    item_rows = [item_headers]
    for _, row in items.iterrows():
        item_rows.append(
            [
                str(row.get("nome", "")),
                format_brl(row.get("preco_kg"), 4),
                f"{as_float(row.get('inclusao_min'), 0.0) or 0.0:.3f}%",
                f"{as_float(row.get('inclusao_max'), 0.0) or 0.0:.3f}%",
                f"{as_float(row.get('inclusao_calculada'), 0.0) or 0.0:.4f}%",
                format_brl(row.get("custo_parcial"), 4),
            ]
        )
    item_table = Table(item_rows, repeatRows=1, colWidths=[72 * mm, 30 * mm, 25 * mm, 25 * mm, 30 * mm, 34 * mm])
    item_table.setStyle(_table_style())
    story.extend([item_table, Spacer(1, 5 * mm), Paragraph("Restrições nutricionais", styles["Heading2"])])

    nutrient_rows = [["Nutriente", "Unidade", "Mínimo", "Máximo", "Resultado", "Situação"]]
    for _, row in constraints.iterrows():
        nutrient_rows.append(
            [
                str(row.get("nutriente", "")),
                str(row.get("unidade", "")),
                _number_or_dash(row.get("minimo")),
                _number_or_dash(row.get("maximo")),
                _number_or_dash(row.get("resultado")),
                str(row.get("situacao", "")),
            ]
        )
    nutrient_table = Table(nutrient_rows, repeatRows=1, colWidths=[35 * mm, 28 * mm, 32 * mm, 32 * mm, 35 * mm, 42 * mm])
    nutrient_table.setStyle(_table_style())
    story.append(nutrient_table)
    doc.build(story)
    return output.getvalue()


def _number_or_dash(value: object) -> str:
    number = as_float(value)
    if number is None:
        return "—"
    return f"{number:.4f}".replace(".", ",")


def _table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FA")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]
    )


def export_filenames(metadata: dict) -> dict[str, str]:
    base = safe_filename(str(metadata.get("nome") or "formulacao"))
    return {"xlsx": f"{base}.xlsx", "pdf": f"{base}.pdf", "csv": f"{base}_ingredientes.csv"}
