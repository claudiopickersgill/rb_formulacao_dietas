"""Conversão dimensional de EM sem alterar a base seca/natural."""
from __future__ import annotations

import math


def em_to_kcal_per_g(value: float, source_unit: str = 'Mcal/kg') -> float:
    if not math.isfinite(value):
        raise ValueError('EM deve ser um número finito.')
    if source_unit == 'Mcal/kg':
        # 1 Mcal = 1000 kcal; 1 kg = 1000 g. O fator resultante é 1.
        return value * (1000.0 / 1000.0)
    if source_unit == 'kcal/g':
        return value
    raise ValueError('Unidade de EM não suportada: ' + source_unit)
