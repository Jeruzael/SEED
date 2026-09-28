"""Narrow, literal B8 differences from immutable historical scenario artifacts."""
from copy import deepcopy


def control_expected(historical):
    expected=deepcopy(historical)
    for key in ('database_footprint','database_page_count'):expected.pop(key,None)
    expected.update(action_distribution={'observe':4,'rest':4},
        action_sequence=['observe']*4+['rest']*4,returned_intervals_seconds=[8]*4+[35]*4,policy_coverage=3,
        q_values=[dict(state_key='charging|calm|ok|day',action='observe',value=.2018844,visits=3),
                  dict(state_key='low|busy|tight|night',action='observe',value=-.216,visits=1),
                  dict(state_key='low|busy|tight|night',action='rest',value=1.09575648,visits=4)])
    if 'prediction_structure' in expected:
        expected['prediction_structure']['method_groups']={'action_specific':16,'global':8,'persistence':8}
        expected['prediction_structure']['evidence_counts']={k:[0,0,2,3,4,5,2,3] for k in expected['prediction_structure']['evidence_counts']}
    return expected


def assert_control(current,historical):
    current=deepcopy(current)
    for key in ('database_footprint','database_page_count'):current.pop(key,None)
    assert current==control_expected(historical)


def curiosity_expected(historical):
    expected=deepcopy(historical)
    # Eligible current load .2 and large observed after-load preserve the B5
    # surprise magnitude and already_reflected semantics under B8's action guard.
    c=expected['policy_reflect']
    c['prediction']['signals']['load_ratio']['value']=.2
    c['reward']=.45
    c['q_value']=.6549999999999999
    c['assessment']['components']['signals']['load_ratio']['sample']=1e300
    c['evaluation']['signals']['load_ratio'].update(actual=1e300,signed_error=1e300,predicted=.2)
    return expected
