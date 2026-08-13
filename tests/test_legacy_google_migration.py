from src.repositories.google_sheets import _convert_legacy_ingredient_values


def test_convert_legacy_ingredient_sheet():
    values = [
        ["Tipo", "Ingredientes", "Classificação", "R$", "MS", "NDT", "PB", "FDN", "FDA", "Se"],
        ["Alimento", "Milho", "Energético", "1,25", "88", "88", "9", "12", "4", "0,1"],
        ["Mineral", "Calcário", "Macromineral", "", "100", "", "", "", "", ""],
    ]

    frame = _convert_legacy_ingredient_values(values)

    assert len(frame) == 2
    assert frame.loc[0, "nome"] == "Milho"
    assert frame.loc[0, "preco_padrao"] == 1.25
    assert frame.loc[0, "NDT"] == 88.0
    assert frame.loc[0, "Se"] == 0.1
    assert frame["ingredient_id"].str.startswith("ing_").all()
