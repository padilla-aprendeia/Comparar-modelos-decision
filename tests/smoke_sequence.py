import app,time,tempfile
from pathlib import Path
from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as directory:
    app.DB=Path(directory)/'smoke.sqlite3'; app.init()
    cfg={'url':'http://localhost:11434','models':[{'name':'d3:4b','kind':'decision'},{'name':'llama3.2:latest','kind':'llm'}], 'catalog':app.DEFAULT_CATALOG,'rows':[{'ID':'smoke','Solicitud':'La farola esta apagada.','Departamento esperado':'alumbrado','Dificultad':'baja'}],'repetitions':1,'timeout':120}
    with TestClient(app.app) as client:
        r=client.post('/api/runs',json=cfg); r.raise_for_status(); ident=r.json()['id']
        while True:
            data=client.get('/api/runs/'+ident).json()
            if data['status']!='en_curso': break
            time.sleep(.5)
        print('status',data['status'],'progress',data['progress'],flush=True)
        print('events',[(e['modelo'],e['evento']) for e in data['lifecycle']],flush=True)
        print('results',[(x['modelo'],x['resultado'],x.get('tiempo_verificado')) for x in data['results']],flush=True)
        if data['status']!='completada' or len(data['results'])!=2 or not all(x.get('tiempo_verificado') for x in data['results']): raise RuntimeError('Smoke test failed')
