"""Persistência por ingredient_id, independente da posição na tabela."""
import pandas as pd
import pytest

from src.pages import formulation as page


@pytest.fixture
def state(monkeypatch):
    state = {}
    monkeypatch.setattr(page.st, 'session_state', state)
    return state


@pytest.fixture
def catalog():
    frame = pd.DataFrame([
        dict(ingredient_id='a',nome='Milho',tipo='Alimento',classificacao='Energético',preco_padrao=1.1,PB=8.5),
        dict(ingredient_id='b',nome='Soja',tipo='Alimento',classificacao='Proteico',preco_padrao=2.2,PB=45),
        dict(ingredient_id='c',nome='Trigo',tipo='Alimento',classificacao='Energético',preco_padrao=3.3,PB=17),
    ])
    return frame.set_index('ingredient_id',drop=False)


def seed_editor(state, catalog):
    full = page._merge_selected_items(['a','b'],catalog)
    state[page.PREFIX+'items_full'] = full
    base,key = page._items_editor_input(full,['a','b'])
    state[key] = dict(edited_rows={0:dict(preco_kg=1.75,inclusao_min=5,inclusao_max=65),
                                  1:dict(preco_kg=2.65,inclusao_min=10,inclusao_max=40)},
                      added_rows=[],deleted_rows=[])
    return key


def test_add_without_calculating_preserves_existing_rows(state,catalog):
    seed_editor(state,catalog)
    page._capture_item_editor_edits()  # Callback da seleção, antes de reconstruir.
    full = page._merge_selected_items(['a','b','c'],catalog)
    base,_ = page._items_editor_input(full,['a','b','c'])
    a,b,c = base.to_dict('records')
    assert (a['preco_kg'],a['inclusao_min'],a['inclusao_max']) == (1.75,5,65)
    assert (b['preco_kg'],b['inclusao_min'],b['inclusao_max']) == (2.65,10,40)
    assert (c['preco_kg'],c['inclusao_min'],c['inclusao_max']) == (3.3,0,100)


def test_reordering_uses_old_editor_positions_and_stable_ids(state,catalog):
    seed_editor(state,catalog)
    page._capture_item_editor_edits()
    full=page._merge_selected_items(['b','c','a'],catalog).set_index('ingredient_id')
    assert full.loc['a','preco_kg']==1.75
    assert full.loc['b','preco_kg']==2.65
    assert full.loc['c','preco_kg']==3.3


def test_remove_preserves_remaining_and_readd_uses_defaults(state,catalog):
    seed_editor(state,catalog)
    page._capture_item_editor_edits()
    remaining=page._merge_selected_items(['b'],catalog)
    state[page.PREFIX+'items_full']=remaining
    result=page._merge_selected_items(['b','a'],catalog).set_index('ingredient_id')
    assert result.loc['b','preco_kg']==2.65
    assert result.loc['a','preco_kg']==1.1


def test_zero_price_free_flag_and_zero_maximum_survive(state,catalog):
    key=seed_editor(state,catalog)
    state[key]['edited_rows']={0:dict(preco_kg=0,sem_custo=True,inclusao_min=0,inclusao_max=0)}
    page._capture_item_editor_edits(key)
    full=page._merge_selected_items(['a','b','c'],catalog).set_index('ingredient_id')
    assert full.loc['a','preco_kg']==0
    assert bool(full.loc['a','sem_custo'])
    assert full.loc['a','inclusao_max']==0


def test_deliberately_cleared_price_does_not_return_to_catalog(state,catalog):
    key=seed_editor(state,catalog)
    state[key]['edited_rows']={0:dict(preco_kg=None)}
    page._capture_item_editor_edits(key)
    full=page._merge_selected_items(['a','b','c'],catalog)
    assert pd.isna(full.iloc[0]['preco_kg'])


def test_current_catalog_composition_wins_and_unknown_fields_are_ignored(state,catalog):
    key=seed_editor(state,catalog)
    state[key]['edited_rows'][0].update(PB=999,nome='Alterado',ingredient_id='errado')
    page._capture_item_editor_edits(key)
    catalog.loc['a','PB']=9.1
    full=page._merge_selected_items(['a','b','c'],catalog).set_index('ingredient_id')
    assert full.loc['a','PB']==9.1
    assert full.loc['a','nome']=='Milho'
    assert full.loc['a','preco_kg']==1.75


def test_pending_saved_diet_cannot_receive_old_editor_deltas(state,catalog):
    seed_editor(state,catalog)
    saved=page._merge_selected_items(['b'],catalog)
    saved['preco_kg']=7.5
    state[page.PREFIX+'load_bundle']=dict(
        metadata=dict(nome='Salva',diet_id='saved',custo_kg=7.5),items=saved,
        constraints=pd.DataFrame([dict(nutriente='PB',minimo=12,maximo=50)]))
    page._load_pending_bundle()
    page._capture_item_editor_edits()
    full=page._merge_selected_items(['b','c'],catalog).set_index('ingredient_id')
    assert full.loc['b','preco_kg']==7.5
    assert state[page.PREFIX+'constraints'].iloc[0]['minimo']==12


def test_reset_does_not_restore_previous_edits(state,catalog):
    seed_editor(state,catalog)
    page._capture_item_editor_edits()
    page._reset_form()
    page._ensure_defaults()
    page._capture_item_editor_edits()
    full=page._merge_selected_items(['a'],catalog)
    assert full.iloc[0]['preco_kg']==1.1


def test_repeated_capture_is_idempotent_and_base_remains_stable(state,catalog):
    key=seed_editor(state,catalog)
    base_before=state[page.ITEMS_EDITOR_BASE_KEY].copy()
    page._capture_item_editor_edits(key)
    first=state[page.PREFIX+'items_full'].copy()
    page._capture_item_editor_edits(key)
    pd.testing.assert_frame_equal(first,state[page.PREFIX+'items_full'])
    pd.testing.assert_frame_equal(base_before,state[page.ITEMS_EDITOR_BASE_KEY])


APP = '''
import pandas as pd
from src.config import NUTRIENT_CODES
from src.models import User
from src.pages.formulation import render
class Catalog:
    def list_ingredients(self, active_only=False):
        rows=[]
        for id,name,price in [('a','Milho',1.1),('b','Soja',2.2),('c','Trigo',3.3)]:
            row=dict.fromkeys(NUTRIENT_CODES,0.0)
            row.update(ingredient_id=id,nome=name,tipo='Alimento',classificacao='Teste',
                       preco_padrao=price,ativo=True,MS=90,PB=20)
            rows.append(row)
        return pd.DataFrame(rows)
render(Catalog(),User('test','test@local','Teste','Administrador'))
'''


def test_streamlit_selection_captures_pending_editor_without_calculate():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_string(APP,default_timeout=20).run()
    assert not app.exception
    app.multiselect[0].set_value(['a','b']).run()
    assert not app.exception
    editor_key='frm_items_editor_'+str(app.session_state[page.ITEMS_EDITOR_REVISION_KEY])
    # Protocolo de delta do próprio st.data_editor, sem chamar o cálculo.
    app.session_state[editor_key]=dict(edited_rows={'0':dict(preco_kg=1.75,inclusao_min=5,inclusao_max=65),
                                                  '1':dict(preco_kg=2.65,inclusao_min=10,inclusao_max=40)},
                                       added_rows=[],deleted_rows=[])
    app.multiselect[0].set_value(['a','b','c']).run()
    assert not app.exception
    full=app.session_state['frm_items_full'].set_index('ingredient_id')
    assert tuple(full.loc['a',['preco_kg','inclusao_min','inclusao_max']])==(1.75,5,65)
    assert tuple(full.loc['b',['preco_kg','inclusao_min','inclusao_max']])==(2.65,10,40)
    assert tuple(full.loc['c',['preco_kg','inclusao_min','inclusao_max']])==(3.3,0,100)
    assert 'frm_result' not in app.session_state
    # A grade de ingredientes envia alterações fora do formulário; a de limites
    # nutricionais mantém a submissão explícita para calcular.
    assert app.dataframe[0].proto.form_id==''
    assert any(grid.proto.form_id=='frm_calculation_form' for grid in app.dataframe)
    app.multiselect[0].set_value(['c','b']).run()
    assert not app.exception
    remaining=app.session_state['frm_items_full'].set_index('ingredient_id')
    assert remaining.loc['b','preco_kg']==2.65
    app.multiselect[0].set_value([]).run()
    assert app.session_state['frm_items_full'].empty
    app.multiselect[0].set_value(['a']).run()
    assert app.session_state['frm_items_full'].iloc[0]['preco_kg']==1.1
