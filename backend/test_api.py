import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from app import database
from app.core.config import Settings
from app.main import app
def test_conversation_crud(monkeypatch,tmp_path):
    cfg=Settings(_env_file=None,sqlite_path=tmp_path/'db.sqlite',chroma_dir=tmp_path/'chroma',upload_dir=tmp_path/'pdfs');monkeypatch.setattr(database,'get_settings',lambda:cfg)
    with TestClient(app) as client:
        created=client.post('/api/conversations',json={'title':'Research','document_ids':[]});assert created.status_code==201;cid=created.json()['id']
        assert client.patch(f'/api/conversations/{cid}',json={'title':'Notes'}).json()['title']=='Notes';assert client.get(f'/api/conversations/{cid}/messages').json()==[];assert client.delete(f'/api/conversations/{cid}').status_code==204
