import io, json
import pandas as pd
import pytest
from fastapi.testclient import TestClient
import app

CAT=app.DEFAULT_CATALOG

def xlsx(rows):
    stream=io.BytesIO(); pd.DataFrame(rows).to_excel(stream,index=False); return stream.getvalue()

def record(**kwargs):
    return {'ID':'001','Solicitud':'Una farola apagada','Departamento esperado':'alumbrado','Dificultad':'baja',**kwargs}

def test_excel_valid_and_evaluation_columns_stay_out():
    data=xlsx([record(Extra='no enviar')]); assert app.parse_file(data,'x.xlsx',CAT)==[record()]

def test_excel_rejects_bad_rows_and_missing_columns():
    with pytest.raises(ValueError,match='duplicado'): app.parse_file(xlsx([record(),record()]),'x.xlsx',CAT)
    with pytest.raises(ValueError,match='departamento desconocido'): app.parse_file(xlsx([record(**{'Departamento esperado':'padron'})]),'x.xlsx',CAT)
    with pytest.raises(ValueError,match='Faltan columnas'): app.parse_file(xlsx([{'ID':'1'}]),'x.xlsx',CAT)

def test_catalog_and_csv():
    with pytest.raises(ValueError,match='duplicados'): app.validate_catalog(CAT+[CAT[0]])
    f='ID,Solicitud,Departamento esperado,Dificultad\n1,Farola,alumbrado,baja\n'.encode(); assert app.parse_file(f,'a.csv',CAT)[0]['ID']=='1'

def test_strict_responses():
    codes=['alumbrado','revision_manual']; assert app.interpret('decision',{'answers':{'departamento':{'type':'choice','choice':'alumbrado'}}},codes)=='alumbrado'
    assert app.interpret('decision',{'answers':{'departamento':{'type':'choice','choice':'extra'}}},codes) is None
    def llm(x):return {'message':{'content':json.dumps(x)}}
    assert app.interpret('llm',llm({'departamento':'alumbrado','claridad':4}),codes)=='alumbrado'
    assert app.interpret('llm',llm({'departamento':'alumbrado','claridad':5}),codes) is None
    assert app.interpret('llm',llm({'departamento':'alumbrado','claridad':4,'otro':'x'}),codes) is None

def test_metrics_denominators():
    cfg={'models':[{'name':'m','kind':'llm'}],'rows':[1,2,3,4,5],'repetitions':1}
    def result(status,expected,obtained,secs):return {'modelo':'m','tipo':'llm','resultado':status,'esperado':expected,'obtenido':obtained,'dificultad':'baja','segundos':secs,'tiempo_verificado':True}
    rows=[result('acierto','alumbrado','alumbrado',1),result('error','revision_manual','alumbrado',3),result('invalida','alumbrado',None,2),result('fallo_tecnico','alumbrado',None,4)]
    m=app.metrics(rows,cfg)[0]; assert (m['previstas'],m['intentadas'],m['validas'],m['aciertos'],m['precision'],m['cobertura'])==(5,4,2,1,50,20)
    assert m['manual_omitida']==1 and m['mediana']==2.5 and m['p95']==3.85 and m['por_minuto']==24

def test_ollama_offline_and_url():
    with TestClient(app.app) as client:
        assert client.get('/api/models',params={'url':'http://127.0.0.1:1'}).status_code==503
        assert client.get('/').status_code==200
    with pytest.raises(ValueError): app.safe_url('https://external.example')

def test_decision_payload_never_sends_truth(monkeypatch):
    captured={}
    class Resp:
        def raise_for_status(self): pass
        def json(self): return {'answers':{'departamento':{'type':'choice','choice':'alumbrado'}}}
    class Client:
        def __init__(self,*a,**k): pass
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def post(self,url,json): captured.update(json); return Resp()
    monkeypatch.setattr(app.httpx,'Client',Client)
    app.OllamaConnector('http://localhost:11434',10).classify('x','decision','farola',CAT,{'keep_alive':'5m'})
    assert captured['state']=='farola' and 'claridad' in captured['questions'] and 'Departamento esperado' not in json.dumps(captured)

def test_end_to_end_run_and_export(tmp_path,monkeypatch):
    import time
    monkeypatch.setattr(app,'DB',tmp_path/'test.sqlite3'); app.init()
    monkeypatch.setattr(app,'inventory',lambda url:{'version':'test','models':[{'name':'mock:latest','capabilities':['completion'],'remote':False}]})
    def classify(self,model,kind,text,cat,settings):
        state[model]={'name':model}
        return 'alumbrado',{'message':{'content':'{"departamento":"alumbrado","claridad":4}'}}
    monkeypatch.setattr(app.OllamaConnector,'classify',classify)
    state={}
    def residency(self, model, keep):
        if keep == 0: state.pop(model,None)
        else: state[model]={'name':model}
        return {'done':True}
    monkeypatch.setattr(app.OllamaConnector,'set_residency',residency)
    monkeypatch.setattr(app.OllamaConnector,'running',lambda self:list(state.values()))
    cfg={'url':'http://localhost:11434','models':[{'name':'mock:latest','kind':'llm'}],'catalog':CAT,'rows':[record()],'repetitions':1}
    with TestClient(app.app) as client:
        response=client.post('/api/runs',json=cfg); assert response.status_code==200
        ident=response.json()['id']
        for _ in range(100):
            data=client.get('/api/runs/'+ident).json()
            if data['status']!='en_curso':break
            time.sleep(.01)
        assert data['status']=='completada' and data['results'][0]['resultado']=='acierto'
        assert data['results'][0]['claridad']==4
        assert data['results'][0]['tiempo_verificado'] is True
        assert [e['evento'] for e in data['lifecycle']]==['carga_verificada','descarga_verificada']
        assert 'alumbrado' in client.get('/api/runs/'+ident+'/export.csv').text
        assert client.get('/api/runs/'+ident+'/config.json').json()['config']['instruction']==app.INSTRUCTION

def test_ui_static_selectors_exist():
    import re
    from html.parser import HTMLParser
    class IDs(HTMLParser):
        def __init__(self):
            super().__init__(); self.ids=set()
        def handle_starttag(self, tag, attrs):
            for key,value in attrs:
                if key=='id': self.ids.add(value)
    parser=IDs()
    parser.feed((app.BASE/'static'/'index.html').read_text(encoding='utf-8'))
    script=(app.BASE/'static'/'app.js').read_text(encoding='utf-8')
    selectors=set(re.findall(r"\$\(['\"]#([\w-]+)['\"]\)",script))
    assert selectors-parser.ids==set()

def test_worker_stops_before_next_model_when_unload_fails(tmp_path,monkeypatch):
    import threading
    monkeypatch.setattr(app,'DB',tmp_path/'state.sqlite3'); app.init()
    names=[]
    monkeypatch.setattr(app.OllamaConnector,'running',lambda self:[{'name':names[-1]}] if names else [])
    def classify(self,model,kind,text,cat,settings):
        if not names: names.append(model)
        return 'alumbrado',{'message':{'content':'{"departamento":"alumbrado","claridad":4}'}}
    monkeypatch.setattr(app.OllamaConnector,'classify',classify)
    monkeypatch.setattr(app.OllamaConnector,'set_residency',lambda self,model,keep: {'done':True})
    cfg={'url':'http://localhost:11434','timeout':10,'models':[{'name':'a','kind':'llm'},{'name':'b','kind':'llm'}],'rows':[record()],'catalog':CAT,'repetitions':1,'retries':0,'temperature':0,'seed':42}
    with app.db() as db: db.execute('INSERT INTO runs VALUES (?,?,?,?,?)',('test','now','en_curso',json.dumps(cfg),'{}'))
    app.worker('test',cfg,threading.Event())
    data=app.get_run('test')
    assert data['status']=='fallida' and names==['a']
    assert [e['evento'] for e in data['lifecycle']]==['carga_verificada','fallo_descarga']
    assert len(data['results'])==1

def test_metrics_excludes_unverified_local_time():
    cfg={'models':[{'name':'m','kind':'llm'}],'rows':[1,2],'repetitions':1}
    base={'modelo':'m','tipo':'llm','resultado':'acierto','esperado':'alumbrado','obtenido':'alumbrado','dificultad':'baja'}
    rows=[dict(base,segundos=2,tiempo_verificado=True),dict(base,segundos=100,tiempo_verificado=False)]
    m=app.metrics(rows,cfg)[0]
    assert (m['mediana'],m['tiempos_incluidos'],m['tiempos_excluidos'],m['por_minuto'])==(2,1,1,30)

def test_models_warm_test_unload_in_order(tmp_path,monkeypatch):
    import threading
    monkeypatch.setattr(app,'DB',tmp_path/'sequence.sqlite3'); app.init()
    state={}; calls=[]
    monkeypatch.setattr(app.OllamaConnector,'running',lambda self:list(state.values()))
    def classify(self,model,kind,text,cat,settings):
        calls.append(('classify',model)); state[model]={'name':model}
        return 'alumbrado',{'message':{'content':'{"departamento":"alumbrado","claridad":4}'}}
    def residency(self,model,keep):
        calls.append(('unload',model)); state.pop(model,None); return {'done':True}
    monkeypatch.setattr(app.OllamaConnector,'classify',classify)
    monkeypatch.setattr(app.OllamaConnector,'set_residency',residency)
    cfg={'url':'http://localhost:11434','timeout':10,'models':[{'name':'a','kind':'llm'},{'name':'b','kind':'llm'}],'rows':[record()],'catalog':CAT,'repetitions':1,'retries':0,'temperature':0,'seed':42}
    with app.db() as db: db.execute('INSERT INTO runs VALUES (?,?,?,?,?)',('test','now','en_curso',json.dumps(cfg),'{}'))
    app.worker('test',cfg,threading.Event())
    assert app.get_run('test')['status']=='completada'
    assert calls==[('classify','a'),('classify','a'),('unload','a'),('classify','b'),('classify','b'),('unload','b')]

def test_start_accepts_decision_without_llm_and_rejects_empty(tmp_path,monkeypatch):
    import time
    monkeypatch.setattr(app,'DB',tmp_path/'decision.sqlite3'); app.init()
    monkeypatch.setattr(app,'inventory',lambda url:{'version':'test','models':[{'name':'decision:latest','capabilities':['decision'],'remote':False}]})
    state={}
    def classify(self,model,kind,text,cat,settings):
        state[model]={'name':model}
        return 'alumbrado',{'answers':{'departamento':{'type':'choice','choice':'alumbrado'}}}
    def residency(self,model,keep):
        state.pop(model,None); return {'done':True}
    monkeypatch.setattr(app.OllamaConnector,'classify',classify)
    monkeypatch.setattr(app.OllamaConnector,'running',lambda self:list(state.values()))
    monkeypatch.setattr(app.OllamaConnector,'set_residency',residency)
    questions=app.default_questions(CAT)
    questions['departamento']['instructions']='Clasifica usando la instrucción modificada.'
    cfg={'url':'http://localhost:11434','models':[{'name':'decision:latest','kind':'decision'}],'catalog':CAT,'questions':questions,'rows':[record()],'repetitions':1}
    with TestClient(app.app) as client:
        assert client.post('/api/runs',json={**cfg,'models':[]}).status_code==400
        response=client.post('/api/runs',json=cfg)
        assert response.status_code==200
        ident=response.json()['id']
        for _ in range(100):
            data=client.get('/api/runs/'+ident).json()
            if data['status']!='en_curso': break
            time.sleep(.01)
        assert data['status']=='completada'
        assert data['results'][0]['modelo']=='decision:latest'
        assert data['config']['questions']==questions
        assert client.get('/api/runs/'+ident+'/config.json').json()['config']['questions']==questions

def test_custom_questions_are_validated_and_sent_to_all_connectors(monkeypatch):
    q=app.default_questions(CAT)
    q['departamento']['instructions']='Instruccion personalizada'
    q['departamento']['criteria']['alumbrado']='Criterio personalizado'
    q['claridad']['instructions']='Evaluar certeza'
    q['claridad']['criteria']=['baja','media','alta']
    payloads=[]
    class Resp:
        def raise_for_status(self): pass
        def json(self):
            if payloads[-1][0].endswith('/api/chat'):
                return {'message':{'content':'{"departamento":"alumbrado","claridad":2}'}}
            return {'answers':{'departamento':{'type':'choice','choice':'alumbrado'}}}
    class Client:
        def __init__(self,*a,**k): pass
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def post(self,url,json,**kwargs): payloads.append((url,json)); return Resp()
    monkeypatch.setattr(app.httpx,'Client',Client)
    monkeypatch.setenv('JEV_API_KEY','test-key')
    settings={'questions':q,'temperature':0,'seed':42,'timeout':2}
    connector=app.OllamaConnector('http://localhost:11434',2)
    assert connector.classify('m','decision','farola',CAT,settings)[0]=='alumbrado'
    assert connector.classify('m','llm','farola',CAT,settings)[0]=='alumbrado'
    assert app.JevConnector().classify('m','jev','farola',CAT,settings)[0]=='alumbrado'
    assert payloads[0][1]['questions']==q and payloads[2][1]['questions']==q
    llm=payloads[1][1]
    assert 'Instruccion personalizada' in llm['messages'][0]['content']
    assert 'Criterio personalizado' in llm['messages'][0]['content']
    assert llm['format']['properties']['claridad']['maximum']==2
    assert all(p['state']=='farola' for _,p in (payloads[0],payloads[2]))

def test_custom_questions_reject_incompatible_changes():
    q=app.default_questions(CAT)
    q['departamento']['criteria'].pop('alumbrado')
    with pytest.raises(ValueError,match='coincidir'): app.validate_questions(q,CAT)
    q=app.default_questions(CAT); q['claridad']['criteria']=['unico']
    with pytest.raises(ValueError,match='2 y 10'): app.validate_questions(q,CAT)
    q=app.default_questions(CAT); q['otra']={'type':'choice'}
    with pytest.raises(ValueError,match='exactamente'): app.validate_questions(q,CAT)
    result={'message':{'content':'{"departamento":"alumbrado","claridad":3}'}}
    assert app.interpret('llm',result,['alumbrado'],3) is None

def test_localhost_normalized_to_ipv4_without_changing_explicit_ipv6():
    assert app.safe_url('http://localhost:11434/')=='http://127.0.0.1:11434'
    assert app.safe_url('http://localhost:3333')=='http://127.0.0.1:3333'
    assert app.safe_url('http://[::1]:11434')=='http://[::1]:11434'
    with pytest.raises(ValueError): app.safe_url('http://localhost.evil.example:11434')

def test_validation_row_number_does_not_depend_on_dataframe_index(monkeypatch):
    frame=pd.DataFrame([record(),record(**{'ID':'002','Solicitud':''})], index=['first','second'])
    monkeypatch.setattr(app.pd,'read_excel',lambda *args,**kwargs:frame)
    with pytest.raises(ValueError,match='Fila 3: solicitud vac'):
        app.parse_file(b'example','example.xlsx',CAT)
