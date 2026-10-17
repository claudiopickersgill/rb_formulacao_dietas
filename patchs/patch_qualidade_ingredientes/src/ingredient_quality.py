"""Classificação conservadora das notas legadas, sem gravar na fonte."""
from __future__ import annotations
import pandas as pd
from .utils import as_bool, normalize_text

IMPORT_NOTE = "Composição adicionada da nova tabela recebida; linha interpretada como MS + perfil mineral (Ca, P, Mg, Na, K, Cl, S, Fe, Cu, Mn, Zn, Co, I, Se)."
BACKFILL_NOTE = "Composição nutricional complementada automaticamente a partir da base original."

def classify_ingredient_notes(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for col in ["qualidade_dados", "observacoes"]:
        if col not in result:
            result[col] = ""
        result[col] = result[col].fillna("").astype(str)
    if result.empty:
        return result
    active = result["ativo"].map(lambda v: as_bool(v, True))
    keys = result["tipo"].map(normalize_text) + "|" + result["nome"].map(normalize_text)
    counts = keys[active].value_counts()
    for idx, row in result.iterrows():
        note = row["qualidade_dados"].strip()
        historical = not active.loc[idx] and (
            note.startswith("Duplicata desativada na migração; mantida para preservar o ID histórico. Registro ativo equivalente: linha ")
            or note == "Ausente na nova tabela recebida; desativado sem exclusão para preservar histórico."
        )
        resolved = note == "Nome duplicado na planilha legada" and counts.get(keys.loc[idx], 0) == 1
        informative = note == IMPORT_NOTE and str(row.get("created_by", "")) == "migracao_etapa2"
        moved = note if historical or resolved or informative else ""
        if not moved and BACKFILL_NOTE in note:
            # Retira só a frase conhecida; preserva qualquer outra pendência.
            moved = BACKFILL_NOTE
            note = note.replace(BACKFILL_NOTE, "").strip("; ")
        elif moved:
            note = ""
        if moved:
            old = row["observacoes"].strip()
            result.at[idx, "observacoes"] = old if moved in old else "\n".join(filter(None, [old, moved]))
            result.at[idx, "qualidade_dados"] = note
    return result

def active_quality_warnings(frame: pd.DataFrame) -> pd.DataFrame:
    frame = classify_ingredient_notes(frame)
    if frame.empty:
        return frame
    return frame[frame["ativo"].map(lambda v: as_bool(v, True)) & frame["qualidade_dados"].str.strip().ne("")].copy()
