import time
from app import OllamaConnector,DEFAULT_CATALOG
c=OllamaConnector('http://localhost:11434',120)
config={'keep_alive':'5m','temperature':0,'seed':42}
for name,kind in [('d3:4b','decision'),('d1:latest','decision'),('nimble-v3:9b','decision'),('laya:latest','decision'),('llama3.2:latest','llm')]:
    start=time.perf_counter()
    try:
        val, data=c.classify(name,kind,'La farola de la plaza está apagada; solicito que la reparen.',DEFAULT_CATALOG,config)
        print(name, 'resultado:',val, 'claridad:', data.get('answers',{}).get('claridad') if kind=='decision' else data.get('message',{}).get('content'), 'segundos:', round(time.perf_counter()-start,2),flush=True)
    except Exception as e: print(name,'ERROR',type(e).__name__,str(e)[:500],flush=True)
