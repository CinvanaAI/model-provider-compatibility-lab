from provider_compat.adapters import OllamaAdapter
from provider_compat.evidence import CompatibilityLedger,evidence_from_success
from provider_compat.lab import attempt_task
from provider_compat.types import ModelRef,ProviderConfig


def test_task_success_does_not_invent_inventory():
    assert evidence_from_success('demo','fixture','extract').can_list_models is None


def test_ollama_preserves_returned_usage():
    config=ProviderConfig(provider='Ollama',provider_key='ollama',base_url='http://localhost:11434')
    model=ModelRef('Ollama','ollama','fixture','Fixture',{})
    adapter=OllamaAdapter(config,transport=lambda *args:(200,{'model':'fixture','done':True,'message':{'content':'retained output'},'prompt_eval_count':12,'eval_count':7,'prompt_eval_cached_count':3}))
    response=adapter.analyze(model,'Synthetic input')
    assert response.response_metadata['usage']['input_tokens']==12
    assert response.response_metadata['usage']['output_tokens']==7
    assert response.response_metadata['raw_usage']['prompt_eval_cached_count']==3
