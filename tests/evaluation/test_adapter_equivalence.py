"""I13 oracle: original trusted cycle versus that cycle under observation."""
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
from pathlib import Path
import pytest
from .test_prediction_boundary import checkpoint


class FixedRng:
    def __init__(self,action):self.action=action
    def random(self):return 0.
    def choice(self,eligible):
        assert self.action in eligible
        return self.action


def _parity_child(pipe,launch,adapted,action,count,maintenance):
    core=None
    try:
        from development.evaluation.bootstrap import install_worker_adapters
        from development.evaluation.channel import LearnerClient
        from development.evaluation.adapters import construct_core,CaptureSession
        from development.evaluation.state import OwnedState
        streams=install_worker_adapters(launch)
        client=LearnerClient(pipe,streams.clock)
        if adapted:
            core=construct_core(launch,streams,client)
        else:
            # Independently bind a test body before the original constructor;
            # control never uses construct_core, SyntheticBody or CaptureSession.
            import seed.organism as organism
            class ControlBody:
                def __init__(self,home):self.key=None
                def begin(self,key):self.key=key;self.perceptions=0;self.action=None
                def perceive(self):
                    phase,subcase,ordinal,_=self.key
                    observation=(client.observation(phase,ordinal,subcase) if self.perceptions==0 else
                                 client.apply(self.action,ordinal))
                    self.perceptions+=1
                    return {**observation,'wall_time':streams.clock.wall()}
            state=OwnedState.fresh(launch.learner,json.loads(launch.settings));state.close()
            organism.Body=ControlBody
            core=organism.SeedOrganism(launch.learner.home)
        core.decisions.rng=FixedRng(action)
        for _ in range(8):core.memory.episode('experience',checkpoint()['state_before'],action='observe')
        original_b3=None
        import seed.organism as organism
        results=[];selections=[];evaluations=[]
        if adapted:
            capture=CaptureSession(client,streams.clock);capture.attach(core)
        else:
            original_b3=organism.evaluate_prediction
            def b3(*args):
                result=original_b3(*args);evaluations.append(result.to_dict())
                streams.clock.stage('measured',ordinal,3)
                return result
            organism.evaluate_prediction=b3
            select=core.decisions.select
            def selected(prepared):
                result=select(prepared)
                selections.append(dict(selection=result.record,prediction=result.prediction,history=prepared['history']))
                core.body.action=result.decision.action
                streams.clock.stage('measured',ordinal,1)
                return result
            core.decisions.select=selected
            for target,name,stage in ((core.learner,'update',3),(core.self_model,'update',4)):
                original=getattr(target,name)
                def spy(*args,_original=original,_stage=stage,**kwargs):
                    streams.clock.stage('measured',ordinal,_stage);return _original(*args,**kwargs)
                setattr(target,name,spy)
        state=OwnedState(launch.learner,core.memory,core.memory.db.monitor)
        before=state.raw_tables()
        for ordinal in range(1,count+1):
            key=('measured','default',ordinal,'pre')
            if adapted:capture.begin(key)
            else:core.body.begin(key)
            result=core.cycle()
            results.append((result.status,result.delay_seconds,result.reason))
            if adapted:
                selections.append(dict(selection=capture.record['selection'],prediction=capture.record['selected_prediction'],history=capture.record['history']))
                evaluations.append(capture.b3_result.to_dict())
            if maintenance and ordinal%8==0:
                streams.clock.stage('measured',ordinal,4)
                core.consolidate(core.memory.get_meta('last_state',{}),provenance='owner_requested')
        # Pickle is test-owned raw inspection, never the learner public channel.
        pipe.send(dict(kind='parity',pid=os.getpid(),before=before,after=state.raw_tables(),results=results,columns={name:[r[1] for r in core.memory.db.execute('PRAGMA table_info('+name+')')] for name in before},
                       selections=selections,b3=evaluations))
    except BaseException:
        import traceback;traceback.print_exc()
        pipe.send(dict(kind='parity-error'))
    finally:
        if core is not None:core.close()
        pipe.close()


def run_path(root,foundation_module,adapted,action,count,maintenance):
    from development.evaluation.contracts import WorkerLaunch,strict_json
    from development.evaluation.channel import ChannelRouter,wire_bytes
    root.mkdir()
    owned=foundation_module('paths').EvaluationRoot.create(root.resolve());cap=owned.assign_learner('a'*32,0)
    journal=foundation_module('checkpoint').ScoreJournal.create(owned,'a'*32) if adapted else None
    class Scenario:
        def initial_observation(self,key):return checkpoint()['state_before']
        def apply_action(self,action,key):return checkpoint()['state_after']
    router=ChannelRouter(Scenario(),journal=journal)
    ctx=multiprocessing.get_context('spawn');parent,child=ctx.Pipe()
    worker=ctx.Process(target=_parity_child,args=(child,WorkerLaunch(cap,b'{"epsilon":1}',3,'a'*64),adapted,action,count,maintenance),name='seed-evaluation-worker')
    worker.start();child.close()
    try:
        while parent.poll(30):
            raw=parent.recv_bytes()
            # multiprocessing.send wraps test-only final pickle; RPC remains
            # bounded closed JSON and contains no evaluator result/truth.
            if not raw.startswith(b'{'):
                import pickle
                result=pickle.loads(raw);break
            message=strict_json(raw)
            parent.send_bytes(wire_bytes(dict(kind='response',value=router.dispatch(message['request']))))
        else:raise AssertionError('parity worker timed out')
        worker.join(5)
        assert result['kind']=='parity',result
        result['journal_count']=len(journal.path.read_bytes().splitlines()) if journal else 0
        return result
    finally:
        if worker.is_alive():worker.terminate();worker.join(5)
        parent.close()
        if journal:journal.close()


def incidental_pid(tables,pid,columns):
    """Only actual PID is incidental; leave every other raw byte/value intact."""
    result=json.loads(json.dumps(tables));audit=[]
    def scrub(value,path):
        if type(value) is dict:
            for k,v in value.items():
                if k=='pid':
                    assert v==pid or v is None,(path,v,pid)
                    audit.append(path+[k]);value[k]='INCIDENTAL_PID'
                else:scrub(v,path+[k])
        elif type(value) is list:
            for i,v in enumerate(value):scrub(v,path+[i])
    # raw_tables returns ordered lists of dictionaries; reserialize only rows
    # whose raw JSON really includes the process PID, audit exact locations.
    for table,rows in result.items():
        for i,row in enumerate(rows):
            for column,v in zip(columns[table],row):
                index=columns[table].index(column)
                if type(v) is str and (column.endswith('_json') or (table=='meta' and column=='value')):
                    try:decoded=json.loads(v)
                    except ValueError:continue
                    prior=len(audit);scrub(decoded,[table,i,column])
                    if len(audit)!=prior:row[index]=json.dumps(decoded,sort_keys=True)
                elif column=='pid':
                    assert v==pid or v is None;row[index]='INCIDENTAL_PID';audit.append([table,i,column])
    return result,audit


@pytest.mark.parametrize('action,count,maintenance',[
    ('observe',1,False),('rest',1,False),('reflect',1,False),('consolidate',1,False),('observe',8,True)])
def test_adapter_matches_original_cycle(tmp_path,foundation_module,action,count,maintenance):
    control=run_path(tmp_path/'control',foundation_module,False,action,count,maintenance)
    adapted=run_path(tmp_path/'adapted',foundation_module,True,action,count,maintenance)
    assert control['pid']!=adapted['pid']
    assert control['results']==adapted['results']
    assert control['selections']==adapted['selections']
    assert control['b3']==adapted['b3']
    assert control['journal_count']==0 and adapted['journal_count']==count
    for phase in ('before','after'):
        left,audit_left=incidental_pid(control[phase],control['pid'],control['columns'])
        right,audit_right=incidental_pid(adapted[phase],adapted['pid'],adapted['columns'])
        assert audit_left==audit_right
        assert left==right,{table:(left[table],right[table]) for table in left if left[table]!=right[table]}


def test_normal_control_has_no_evaluation_dependency(tmp_path):
    shutil.copytree('seed',tmp_path/'seed',ignore=shutil.ignore_patterns('__pycache__'))
    script='''from pathlib import Path
from seed import organism
class Body:
    def __init__(self,home):pass
    def perceive(self):return dict(battery_pct=80,charging=True,load_ratio=.2,disk_free_pct=75,network=True,local_hour=12)
organism.Body=Body
core=organism.SeedOrganism(Path('home'))
assert core.cycle().status=='completed'
assert core.memory.db.execute('SELECT COUNT(*) FROM transitions').fetchone()[0]==1
core.close()
import sys
assert not any(n.startswith('development.evaluation') for n in sys.modules)
'''
    result=subprocess.run([sys.executable,'-c',script],cwd=tmp_path,capture_output=True,text=True,
                          env={**os.environ,'PYTHONPATH':str(tmp_path)},timeout=30)
    assert result.returncode==0,result.stderr
    assert not (tmp_path/'development').exists()
