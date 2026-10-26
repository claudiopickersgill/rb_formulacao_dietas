from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Nutrient:
    code: str
    label: str
    unit: str
    group: str


NUTRIENTS: tuple[Nutrient, ...] = (
    Nutrient("MS", "Matéria seca", "%", "Macronutrientes"),
    Nutrient("NDT", "Nutrientes digestíveis totais", "%", "Macronutrientes"),
    Nutrient("PB", "Proteína bruta", "%", "Macronutrientes"),
    Nutrient("FDN", "Fibra em detergente neutro", "%", "Macronutrientes"),
    Nutrient("FDA", "Fibra em detergente ácido", "%", "Macronutrientes"),
    Nutrient("EE", "Extrato etéreo", "%", "Macronutrientes"),
    Nutrient("MM", "Matéria mineral", "%", "Macronutrientes"),
    Nutrient("FB", "Fibra bruta", "%", "Macronutrientes"),
    Nutrient("AMIDO", "Amido", "%", "Macronutrientes"),
    Nutrient("EM", "Energia metabolizável", "Mcal/kg", "Macronutrientes"),
    Nutrient("CA", "Cálcio", "%", "Macrominerais"),
    Nutrient("P", "Fósforo", "%", "Macrominerais"),
    Nutrient("Mg", "Magnésio", "%", "Macrominerais"),
    Nutrient("Na", "Sódio", "%", "Macrominerais"),
    Nutrient("K", "Potássio", "%", "Macrominerais"),
    Nutrient("Cl", "Cloro", "%", "Macrominerais"),
    Nutrient("S", "Enxofre", "%", "Macrominerais"),
    Nutrient("Fe", "Ferro", "%", "Microminerais"),
    Nutrient("Cu", "Cobre", "%", "Microminerais"),
    Nutrient("Mn", "Manganês", "%", "Microminerais"),
    Nutrient("Zn", "Zinco", "%", "Microminerais"),
    Nutrient("Co", "Cobalto", "%", "Microminerais"),
    Nutrient("I", "Iodo", "%", "Microminerais"),
    Nutrient("Se", "Selênio", "%", "Microminerais"),
    Nutrient("Lys", "Lisina", "%", "Aminoácidos"),
    Nutrient("Met", "Metionina", "%", "Aminoácidos"),
    Nutrient("Thr", "Treonina", "%", "Aminoácidos"),
    Nutrient("Phe", "Fenilalanina", "%", "Aminoácidos"),
    Nutrient("Leu", "Leucina", "%", "Aminoácidos"),
    Nutrient("Ile", "Isoleucina", "%", "Aminoácidos"),
    Nutrient("Val", "Valina", "%", "Aminoácidos"),
    Nutrient("His", "Histidina", "%", "Aminoácidos"),
    Nutrient("Arg", "Arginina", "%", "Aminoácidos"),
    Nutrient("Tyr", "Tirosina", "%", "Aminoácidos"),
)

NUTRIENT_CODES = [n.code for n in NUTRIENTS]
NUTRIENT_BY_CODE = {n.code: n for n in NUTRIENTS}
AMINO_ACID_CODES = [n.code for n in NUTRIENTS if n.group == "Aminoácidos"]
DEFAULT_CONSTRAINTS = [
    "MS",
    "NDT",
    "PB",
    "FDN",
    "FDA",
    "AMIDO",
    "CA",
    "P",
]
ROLES = ("Administrador", "Formulador", "Consulta")

INGREDIENT_COLUMNS = [
    "ingredient_id",
    "tipo",
    "nome",
    "classificacao",
    "formula_quimica",
    "fonte",
    "preco_padrao",
    *NUTRIENT_CODES,
    "ativo",
    "qualidade_dados",
    "observacoes",
    "cqbal_dados",
    "created_by",
    "created_at",
    "updated_at",
]

USER_COLUMNS = [
    "user_id",
    "email",
    "nome",
    "perfil",
    "ativo",
    "password_hash",
    "created_at",
    "updated_at",
    "last_login",
]

DIET_COLUMNS = [
    "diet_id",
    "parent_diet_id",
    "nome",
    "descricao",
    "categoria_animal",
    "base",
    "objetivo",
    "proprietario",
    "status",
    "custo_kg",
    "created_at",
    "updated_at",
]

DIET_ITEM_COLUMNS = [
    "diet_id",
    "ingredient_id",
    "ordem",
    "tipo",
    "nome",
    "classificacao",
    "preco_kg",
    "sem_custo",
    "inclusao_min",
    "inclusao_max",
    "inclusao_calculada",
    "custo_parcial",
    *NUTRIENT_CODES,
]

DIET_CONSTRAINT_COLUMNS = [
    "diet_id",
    "nutriente",
    "unidade",
    "minimo",
    "maximo",
    "resultado",
    "situacao",
]

AUDIT_COLUMNS = [
    "audit_id",
    "timestamp",
    "usuario",
    "acao",
    "entidade",
    "entity_id",
    "detalhes",
]

TABLE_SCHEMAS = {
    "ingredientes": INGREDIENT_COLUMNS,
    "usuarios": USER_COLUMNS,
    "dietas": DIET_COLUMNS,
    "dieta_ingredientes": DIET_ITEM_COLUMNS,
    "dieta_restricoes": DIET_CONSTRAINT_COLUMNS,
    "auditoria": AUDIT_COLUMNS,
}

# Campos que representam data/hora e devem permanecer no fuso do aplicativo.
TIMESTAMP_COLUMNS_BY_TABLE = {
    "ingredientes": ["created_at", "updated_at"],
    "usuarios": ["created_at", "updated_at", "last_login"],
    "dietas": ["created_at", "updated_at"],
    "auditoria": ["timestamp"],
}
