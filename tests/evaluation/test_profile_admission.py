"""R5: the complete requested execution profile is bound at admission."""
from dataclasses import replace
import hashlib
import json
import pytest


def profile(foundation_module):
    p=foundation_module('profile')
    return p.Profile('a'*40,True,'b'*64,7,'0.2','CPython','3.13.1','3.46.0',('A','B'),'Darwin','arm64')


def requested(value):
    # Independent canonical literal envelope, all values are JSON scalar/list fields.
    fields=value.as_dict(); fields['sqlite_compile']=list(fields['sqlite_compile'])
    raw=(json.dumps({'schema':'b10_execution_profile_v1','profile':fields},sort_keys=True,separators=(',',':'))+'\n').encode('ascii')
    return dict(source_commit=value.source_commit,lock_digest=value.lock_digest,profile_digest=hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize('bad',['0'*64,'1'*64,None])
def test_declared_profile_digest_required(foundation_module,bad):
    p=foundation_module('profile'); value=profile(foundation_module); request=requested(value)
    if bad is None: request.pop('profile_digest')
    else: request['profile_digest']=bad
    with pytest.raises(ValueError): p.require_source(request,value)


@pytest.mark.parametrize('field,value',[('python_version','3.13.2'),('sqlite_version','3.47.0'),('sqlite_compile',('A','C')),('adapter_version',2),('clock_version','changed'),('architecture','x86_64')])
def test_runtime_profile_change_rejected(foundation_module,field,value):
    p=foundation_module('profile'); original=profile(foundation_module)
    with pytest.raises(ValueError): p.require_source(requested(original),replace(original,**{field:value}))


def test_matching_complete_profile_accepted(foundation_module):
    p=foundation_module('profile'); value=profile(foundation_module)
    p.require_source(requested(value),value)
