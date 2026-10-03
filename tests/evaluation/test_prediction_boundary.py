"""R8: checkpoint prediction is the closed producer schema, bound to action."""
import copy
import json
import pytest


def checkpoint():
    from seed.predictor import empty_history_batch
    state={'battery_pct':80,'charging':True,'load_ratio':.2,'disk_free_pct':75,'network':True,'local_hour':12}
    prediction=empty_history_batch(state,('observe',)).predictions['observe']
    return dict(phase='measured',subcase='default',transition_ordinal=1,history_cutoff_id=0,
                state_before=state,selected_action='observe',prediction=prediction,state_after=state)


@pytest.mark.parametrize('mutation',['wrong_action','top','nested','private','nonfinite','malformed'])
def test_closed_prediction_boundary_rejects_mutations(foundation_module,mutation):
    c=foundation_module('contracts'); value=checkpoint()
    prediction=value['prediction']
    if mutation=='wrong_action': prediction['action']='rest'
    elif mutation=='top': prediction['unknown']=1
    elif mutation=='nested': prediction['signals']['load_ratio']['extra']=1
    elif mutation=='private': prediction['signals']['load_ratio']['truth']='PRIVATE_EVALUATOR_SENTINEL'
    elif mutation=='nonfinite': prediction['signals']['load_ratio']['value']=float('nan')
    else: prediction['signals']['load_ratio']={'status':'predicted','value':.2}
    with pytest.raises(ValueError): c.decode_message(json.dumps(value).encode(),'checkpoint')


def test_existing_b2_prediction_accepted(foundation_module):
    value=checkpoint()
    assert foundation_module('contracts').decode_message(json.dumps(value).encode(),'checkpoint')==value


def test_prediction_size_cap_retained(foundation_module):
    value=checkpoint(); value['prediction']['huge']=['x'*4096]*5
    with pytest.raises(ValueError): foundation_module('contracts').decode_message(json.dumps(value).encode(),'checkpoint')
