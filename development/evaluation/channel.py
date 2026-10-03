"""Closed byte channel. Private scenario capabilities stay in the parent."""
import json
import threading
from .contracts import ContractError, PreUpdateEvidence, decode_message, fields, strict_json, validate_event_key, validate_observation, MESSAGE_BYTES
from .registry import ACTIONS


def wire_bytes(value):
    try:
        raw=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
        strict_json(raw)
        return raw
    except (ValueError,TypeError,UnicodeError):
        raise ContractError() from None


def validate_request(request):
    # Validate detached bytes too, to impose depth/entry/nonfinite limits before dispatch.
    value=strict_json(wire_bytes(request))
    fields(value,('operation',),('key','action','evidence'))
    op=value['operation']
    if op=='action_catalog':
        fields(value,('operation',))
    elif op=='observation':
        fields(value,('operation','key'))
        if validate_event_key(value['key'])[3]!='pre':
            raise ContractError()
    elif op=='apply':
        fields(value,('operation','key','action'))
        if validate_event_key(value['key'])[3]!='action' or value['action'] not in ACTIONS:
            raise ContractError()
    elif op=='checkpoint':
        fields(value,('operation','evidence'))
        decode_message(wire_bytes(value['evidence']), 'checkpoint')
    else:
        raise ContractError()
    return value


class ChannelRouter:
    """Parent endpoint with an explicit fixed operation table, no reflection."""
    def __init__(self, scenario, *, journal=None):
        self._scenario=scenario
        self._journal=journal
        self._checkpoint_pending=None
        self._before=None
        self._last={}
        self._pending=None
        self._lock=threading.Lock()
        self.failed=False

    def dispatch(self, request):
        value=validate_request(request)
        if not self._lock.acquire(blocking=False):
            raise ContractError()
        try:
            if self.failed:
                raise ContractError()
            applied=False
            op=value['operation']
            if op=='action_catalog':
                return {'actions':list(ACTIONS)}
            if op=='checkpoint':
                if self._journal is None or self._checkpoint_pending is None:
                    raise ContractError()
                evidence=value['evidence']
                key=(evidence['phase'],evidence['subcase'],evidence['transition_ordinal'])
                expected,action,before,after=self._checkpoint_pending
                if key!=expected or evidence['selected_action']!=action or evidence['state_before']!=before or evidence['state_after']!=after:
                    raise ContractError()
                # Private scores remain parent-side; the response is closed constant only.
                token=self._journal.ack(PreUpdateEvidence(wire_bytes(evidence)))
                if token!='SCORE_ACK':
                    raise ContractError()
                self._checkpoint_pending=None
                return {'token':'SCORE_ACK'}
            key=validate_event_key(value['key'])
            identity=key[:2]
            if op=='observation':
                if self._pending is not None or (self._journal is not None and self._checkpoint_pending is not None) or key[2]!=self._last.get(identity,0)+1:
                    raise ContractError()
                result=validate_observation(self._scenario.initial_observation(key))
                self._before=dict(result)
                self._pending=key[:3]
            else:
                if self._pending!=key[:3]:
                    raise ContractError()
                applied=True
                result=validate_observation(self._scenario.apply_action(value['action'],key))
                self._checkpoint_pending=(key[:3],value['action'],self._before,dict(result))
                self._last[identity]=key[2]
                self._pending=None
            return strict_json(wire_bytes(result))
        except BaseException:
            if locals().get('applied',False) or locals().get('op')=='checkpoint': self.failed=True
            if locals().get('op')=='checkpoint':
                # Parent preserves protocol/storage classification. No scoring
                # import is reachable from this shared worker transport module.
                raise
            # Fixed errors never disclose exception messages, truth, or root names.
            raise ContractError() from None
        finally:
            self._lock.release()


class LearnerClient:
    """Worker endpoint owns only its byte pipe, public key, and logical clock."""
    def __init__(self, connection, clock=None):
        self._connection,self._clock=connection,clock
        self._pending=None
        self._busy=False
        self.failed=False

    def _rpc(self, request):
        validate_request(request)
        if self.failed or self._busy or self._connection is None:
            raise ContractError()
        self._busy=True
        try:
            self._connection.send_bytes(wire_bytes({'kind':'request','request':request}))
            if request['operation']=='checkpoint' and not self._connection.poll(10):
                raise ContractError()
            reply=strict_json(self._connection.recv_bytes(MESSAGE_BYTES))
            fields(reply,('kind','value'))
            if reply['kind']!='response':
                raise ContractError()
            return reply['value']
        except (OSError,EOFError,ValueError):
            self.failed=True
            raise ContractError() from None
        finally:
            self._busy=False

    def observation(self, phase, ordinal, subcase='default'):
        if self._pending is not None:
            raise ContractError()
        key=[phase,subcase,ordinal,'pre']
        validate_event_key(key)
        if self._clock:
            self._clock.stage(phase,ordinal,0)
        value=validate_observation(self._rpc({'operation':'observation','key':key}))
        self._pending=key[:3]
        return value

    def action_catalog(self):
        value=self._rpc({'operation':'action_catalog'})
        fields(value,('actions',))
        if value['actions']!=list(ACTIONS):
            raise ContractError()
        return tuple(value['actions'])

    def apply(self, action, ordinal):
        if self.failed:
            raise ContractError()
        if self._pending is None or self._pending[2]!=ordinal:
            raise ContractError()
        key=self._pending+['action']
        validate_request({'operation':'apply','key':key,'action':action})
        if self._clock:
            self._clock.stage(key[0],ordinal,2)
        try:
            value=validate_observation(self._rpc({'operation':'apply','key':key,'action':action}))
        except BaseException:
            self.failed=True
            raise ContractError() from None
        self._pending=None
        return value

    def send_checkpoint(self, evidence):
        try:
            if type(evidence) is not PreUpdateEvidence:
                raise ContractError()
            value=decode_message(evidence.body,'checkpoint')
            reply=self._rpc({'operation':'checkpoint','evidence':value})
            decode_message(wire_bytes(reply),'acknowledgment')
            if self._clock:
                self._clock.stage(value['phase'],value['transition_ordinal'],3)
            return 'SCORE_ACK'
        except BaseException:
            self.failed=True
            raise ContractError() from None
