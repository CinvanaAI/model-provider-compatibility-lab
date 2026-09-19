"""Actual adapter and evidence ledger, with a transparent in-memory transport."""
import json,tempfile
from pathlib import Path
from provider_compat import CompatibilityLedger,attempt_task
from provider_compat.adapters import OllamaAdapter
from provider_compat.types import ProviderConfig,ModelRef,ProviderError


def demonstrate(path):
    calls=[]
    def transport(method,url,headers,payload,timeout):
        calls.append({'method':method,'model':payload['model']})
        if payload['model']=='missing-fixture':raise ProviderError('unknown model',status_code=404)
        if payload['model']=='timeout-fixture':raise ProviderError('connection timed out',error_type='connection_error')
        return 200,{'model':payload['model'],'done':True,'message':{'content':'{"owner":"Morgan"}'},'prompt_eval_count':12,'eval_count':7}
    adapter=OllamaAdapter(ProviderConfig('Synthetic Ollama','demo','http://localhost:11434'),transport)
    ledger=CompatibilityLedger(path);outputs=[]
    for name in ['working-fixture','missing-fixture','timeout-fixture']:
        try:
            response=attempt_task(adapter,ModelRef('Synthetic Ollama','demo',name,name),'extract_owner','Morgan owns this item.',ledger)
            outputs.append({'model':name,'text':response.raw_output,'usage':response.response_metadata['usage']})
        except ProviderError:pass
    records=ledger.load()['records']
    for record in records:record.pop('attempted_at',None)
    return {'mode':'Synthetic HTTP; actual adapter normalization and attempt ledger','request':'Morgan owns this item.','outputs':outputs,'records':records,'transport_calls':len(calls),'network_calls':0}


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='compat-demo-') as scratch:print(json.dumps(demonstrate(Path(scratch)/'ledger.json'),indent=2))
