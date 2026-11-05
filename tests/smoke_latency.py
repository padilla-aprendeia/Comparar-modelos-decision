import time,httpx,json
import app
base='http://127.0.0.1:11434'; model='laya:latest'; conn=app.OllamaConnector(base,120)
if conn.running():
    print('Prueba omitida: Ollama ya tiene modelos cargados.'); raise SystemExit(0)
q=app.default_questions(app.DEFAULT_CATALOG); payload={'model':model,'state':'Una farola esta apagada.','questions':q,'keep_alive':-1}
try:
    with httpx.Client(timeout=120,trust_env=False) as c:
        r=c.post(base+'/v1/systemone',json=payload); r.raise_for_status()
    print('Modelo cargado:',bool(conn.loaded(model)),flush=True)
    for host in ['localhost','127.0.0.1','localhost','127.0.0.1']:
        start=time.perf_counter()
        with httpx.Client(timeout=120,trust_env=False) as c:
            r=c.post('http://'+host+':11434/v1/systemone',json=payload); r.raise_for_status(); result=r.json()
        print(host,'s:',round(time.perf_counter()-start,3),'input_tokens:',result.get('usage',{}).get('input_tokens'),flush=True)
finally:
    conn.set_residency(model,0); print('Descargado:',not bool(conn.loaded(model)),flush=True)
