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
    Nutrient("AMIDO", "Amido", "%", "Macronutrientes"),
    Nutrient("CA", "Cálcio", "%", "Macrominerais"),
    Nutrient("P", "Fósforo", "%", "Macrominerais"),
    Nutrient("Mg", "Magnésio", "%", "Macrominerais"),
    Nutrient("Na", "Sódio", "%", "Macrominerais"),
    Nutrient("K", "Potássio", "%", "Macrominerais"),
    Nutrient("Cl", "Cloro", "%", "Macrominerais"),
    Nutrient("S", "Enxofre", "%", "Macrominerais"),
    Nutrient("Fe", "Ferro", "mg/kg", "Microminerais"),
    Nutrient("Cu", "Cobre", "mg/kg", "Microminerais"),
    Nutrient("Mn", "Manganês", "mg/kg", "Microminerais"),
    Nutrient("Zn", "Zinco", "mg/kg", "Microminerais"),
    Nutrient("Co", "Cobalto", "mg/kg", "Microminerais"),
    Nutrient("I", "Iodo", "mg/kg", "Microminerais"),
    Nutrient("Se", "Selênio", "mg/kg", "Microminerais"),
)

NUTRIENT_CODES = [n.code for n in NUTRIENTS]
NUTRIENT_BY_CODE = {n.code: n for n in NUTRIENTS}
DEFAULT_CONSTRAINTS = ["NDT", "PB", "FDN", "FDA", "CA", "P"]
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
