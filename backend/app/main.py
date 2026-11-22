import json,logging,uuid
from pathlib import Path
from fastapi import BackgroundTasks,FastAPI,File,HTTPException,UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.core.config import get_settings
from app.database import connection,init_db
from app.schemas import ConversationCreate,ConversationPatch,MessageCreate
from app.services import ingest,file_hash,delete_document,get_collection,retrieve,rerank,complete,rewrite_query,update_summary,assemble
# API APPLICATION
# FastAPI setup, CORS policy, database initialization, and health check.
logging.basicConfig(level=logging.INFO)
log=logging.getLogger('pdf-rag')
app=FastAPI(title='Local PDF RAG',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
@app.on_event('startup')
def startup(): init_db()
@app.get('/api/health')
def health(): return {'status':'ok'}
# 1. OFFLINE PDF KNOWLEDGE PREPARATION
# Uploads are saved and registered here; the ingestion pipeline runs as a
# background task. The remaining endpoints list, serve, and remove documents.
@app.post('/api/documents/upload',status_code=202)
async def upload(background:BackgroundTasks,file:UploadFile=File(...)):
    s=get_settings()
    if file.content_type!='application/pdf' and not (file.filename or '').lower().endswith('.pdf'): raise HTTPException(415,'Only PDF files are accepted')
    name=Path(file.filename or 'document.pdf').name; doc_id=str(uuid.uuid4()); path=s.upload_dir/f'{doc_id}.pdf'; size=0
    with path.open('wb') as out:
        while block:=await file.read(1024*1024):
            size+=len(block)
            if size>s.max_upload_mb*1024*1024:
                path.unlink(missing_ok=True); raise HTTPException(413,f'PDF exceeds {s.max_upload_mb} MB')
            out.write(block)
    digest=file_hash(path)
    with connection() as db:
        prior=db.execute('SELECT id,status FROM documents WHERE sha256=?',(digest,)).fetchone()
        if prior:
            path.unlink(missing_ok=True); return {'document_id':prior['id'],'status':prior['status'],'duplicate':True}
        db.execute("INSERT INTO documents(id,filename,sha256,status) VALUES(?,?,?,'processing')",(doc_id,name,digest))
    background.add_task(ingest,doc_id,name,path)
    return {'document_id':doc_id,'filename':name,'status':'processing','duplicate':False}
@app.get('/api/documents')
def documents():
    with connection() as db:return [dict(r) for r in db.execute('SELECT id,filename,page_count,title,status,error,created_at FROM documents ORDER BY created_at DESC')]
@app.get('/api/documents/{doc_id}')
def document(doc_id:str):
    with connection() as db:r=db.execute('SELECT id,filename,page_count,title,status,error,created_at FROM documents WHERE id=?',(doc_id,)).fetchone()
    if not r:raise HTTPException(404,'Document not found')
    return dict(r)
@app.get('/api/documents/{doc_id}/status')
def document_status(doc_id:str):return document(doc_id)
@app.get('/api/documents/{doc_id}/file')
def pdf_file(doc_id:str):
    with connection() as db:r=db.execute('SELECT filename FROM documents WHERE id=?',(doc_id,)).fetchone()
    if not r:raise HTTPException(404,'Document not found')
    return FileResponse(get_settings().upload_dir/f'{doc_id}.pdf',media_type='application/pdf',filename=r['filename'],content_disposition_type='inline')
@app.delete('/api/documents/{doc_id}',status_code=204)
def remove_document(doc_id:str):
    with connection() as db:
        if not db.execute('SELECT 1 FROM documents WHERE id=?',(doc_id,)).fetchone():raise HTTPException(404,'Document not found')
        db.execute('DELETE FROM documents WHERE id=?',(doc_id,))
        for c in db.execute('SELECT id,selected_document_ids FROM conversations').fetchall():
            ids=[x for x in json.loads(c['selected_document_ids']) if x!=doc_id]
            db.execute('UPDATE conversations SET selected_document_ids=? WHERE id=?',(json.dumps(ids),c['id']))
    delete_document(doc_id)
    for ext in ('.pdf','.parents.json'):get_settings().upload_dir.joinpath(doc_id+ext).unlink(missing_ok=True)
# CONVERSATION AND CHAT HISTORY API
# Creates and manages conversations, selected document IDs, messages, and memory.
@app.post('/api/conversations',status_code=201)
def create_conversation(body:ConversationCreate):
    cid=str(uuid.uuid4())
    with connection() as db:db.execute('INSERT INTO conversations(id,title,selected_document_ids) VALUES(?,?,?)',(cid,body.title,json.dumps(body.document_ids)))
    return {'id':cid,'title':body.title,'document_ids':body.document_ids,'summary':''}
@app.get('/api/conversations')
def conversations():
    with connection() as db:rows=db.execute('SELECT * FROM conversations ORDER BY updated_at DESC').fetchall()
    return [{'id':r['id'],'title':r['title'],'summary':r['summary'],'document_ids':json.loads(r['selected_document_ids']),'updated_at':r['updated_at']} for r in rows]
def get_conversation(cid):
    with connection() as db:
        c=db.execute('SELECT * FROM conversations WHERE id=?',(cid,)).fetchone()
        if not c:raise HTTPException(404,'Conversation not found')
        msgs=db.execute('SELECT id,role,content,sources_json,created_at FROM messages WHERE conversation_id=? ORDER BY id',(cid,)).fetchall()
    return {'id':c['id'],'title':c['title'],'summary':c['summary'],'document_ids':json.loads(c['selected_document_ids']),'messages':[{'id':m['id'],'role':m['role'],'content':m['content'],'sources':json.loads(m['sources_json']),'created_at':m['created_at']} for m in msgs]}
@app.get('/api/conversations/{cid}')
def conversation(cid:str):return get_conversation(cid)
@app.patch('/api/conversations/{cid}')
def patch_conversation(cid:str,body:ConversationPatch):
    with connection() as db:
        if body.title is not None:db.execute('UPDATE conversations SET title=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(body.title,cid))
        if body.document_ids is not None:db.execute('UPDATE conversations SET selected_document_ids=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(json.dumps(body.document_ids),cid))
        if not db.execute('SELECT 1 FROM conversations WHERE id=?',(cid,)).fetchone():raise HTTPException(404,'Conversation not found')
    return get_conversation(cid)
@app.delete('/api/conversations/{cid}',status_code=204)
def delete_conversation(cid:str):
    with connection() as db:
        cur=db.execute('DELETE FROM conversations WHERE id=?',(cid,))
        if not cur.rowcount:raise HTTPException(404,'Conversation not found')
@app.get('/api/conversations/{cid}/messages')
def messages(cid:str):return get_conversation(cid)['messages']
# 2. ONLINE RAG CHAT PIPELINE
# Query understanding -> hybrid retrieval -> reranking -> context assembly ->
# local LLM response -> citation persistence and rolling conversation memory.
@app.post('/api/conversations/{cid}/messages')
def chat(cid:str,body:MessageCreate):
    cfg=get_settings();question=body.content.strip()

    # Load conversation memory and confirm that selected PDFs finished ingestion.
    with connection() as db:
        conv=db.execute('SELECT * FROM conversations WHERE id=?',(cid,)).fetchone()
        if not conv:raise HTTPException(404,'Conversation not found')
        requested=json.loads(conv['selected_document_ids']);recent=list(reversed(db.execute('SELECT role,content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?',(cid,cfg.recent_message_limit)).fetchall()));summary=conv['summary']
        ready=[]
        if requested:
            marks=','.join('?' for _ in requested)
            ready=[r['id'] for r in db.execute(f"SELECT id FROM documents WHERE status='ready' AND id IN ({marks})",requested)]
    if not requested:raise HTTPException(409,'Select a ready PDF before asking a document question.')
    if requested and not ready:raise HTTPException(409,'Selected documents are still processing or failed; wait until ingestion is ready.')
    recent_text='\n'.join(f"{m['role']}: {m['content']}" for m in recent)

    # Rewrite short follow-up questions using the recent conversation context.
    try:optimized=rewrite_query(question,summary,recent_text)
    except RuntimeError as exc:raise HTTPException(503,str(exc)) from exc
    # Read indexed child passages from Chroma for the selected ready documents.
    records=[]
    if ready:
        result=get_collection().get(where={'document_id':{'$in':ready}},include=['documents','metadatas'])
        records=[{'id':i,'text':t,'metadata':m} for i,t,m in zip(result['ids'],result['documents'],result['metadatas'])]
        if not records:raise HTTPException(503,'This PDF is marked ready, but its text index is empty. Remove the PDF and upload it again to rebuild its index.')
    # Retrieve candidates with vector + keyword search, then rerank them.
    found=retrieve(optimized,ready,records) if ready and records else []
    if not found:
        # Fail closed: do not ask the LLM to answer without relevant PDF evidence.
        selected=[]
        answer='That information is not present in the selected PDF.'
    else:
        try:selected=rerank(optimized,found,cfg.rerank_top_k)
        except Exception:
            log.exception('Reranker failed; using hybrid retrieval order')
            selected=found[:cfg.rerank_top_k]
    # Attach parent-section context while preserving each passage's citation data.
    for doc_id in ready:
        pp=cfg.upload_dir/f'{doc_id}.parents.json'
        parents=json.loads(pp.read_text(encoding='utf-8')) if pp.exists() else {}
        for r in selected:
            if r['metadata'].get('document_id')==doc_id:r['parent_text']=parents.get(r['metadata'].get('parent_chunk_id'),{}).get('text',r['text'])
    # Generate only when retrieval supplied evidence; otherwise use the fixed
    # abstention above, independent of the language model's output.
    if selected:
        prompt=assemble(question,summary,recent_text,selected)
        try:answer=complete(prompt)
        except RuntimeError as exc:raise HTTPException(503,str(exc)) from exc
    # Persist the turn, its source citations, and retrieved chunks for memory.
    sources=[]
    for r in selected:
        m=r['metadata'];source={'document_id':m['document_id'],'filename':m['filename'],'page_number':m['page_number'],'section_title':m.get('section_title',''),'chunk_id':m['child_chunk_id']}
        if source not in sources:sources.append(source)
    with connection() as db:
        db.execute('INSERT INTO messages(conversation_id,role,content) VALUES(?,?,?)',(cid,'user',question))
        db.execute('INSERT INTO messages(conversation_id,role,content,sources_json) VALUES(?,?,?,?)',(cid,'assistant',answer,json.dumps(sources)))
        db.execute("UPDATE conversations SET updated_at=CURRENT_TIMESTAMP,last_topic=?,title=CASE WHEN title='New chat' THEN ? ELSE title END WHERE id=?",(optimized,question[:60],cid))
        for r in selected:
            m=r['metadata'];db.execute('INSERT OR IGNORE INTO retrieved_chunks VALUES(?,?,?,?)',(cid,m['child_chunk_id'],m['page_number'],m.get('section_title','')))
        count=db.execute('SELECT COUNT(*) FROM messages WHERE conversation_id=?',(cid,)).fetchone()[0]
        if count and count%cfg.summary_every_messages==0:
            rows=db.execute('SELECT role,content FROM messages WHERE conversation_id=? ORDER BY id',(cid,)).fetchall();turns='\n'.join(f"{x['role']}: {x['content']}" for x in rows)
            try:new_summary=update_summary(summary,turns)
            except RuntimeError:log.exception('Summary update failed');new_summary=summary
            db.execute('UPDATE conversations SET summary=? WHERE id=?',(new_summary,cid))
    return {'answer':answer,'sources':sources,'conversation_id':cid,'rewritten_query':optimized}
# CONVERSATION MEMORY RESET
# Clears chat turns and the rolling summary while keeping the conversation.
@app.post('/api/conversations/{cid}/clear')
def clear_conversation(cid: str):
    with connection() as db:
        if not db.execute('SELECT 1 FROM conversations WHERE id=?',(cid,)).fetchone():
            raise HTTPException(404,'Conversation not found')
        db.execute('DELETE FROM messages WHERE conversation_id=?',(cid,))
        db.execute("UPDATE conversations SET summary='',last_topic='',title='New chat',updated_at=CURRENT_TIMESTAMP WHERE id=?",(cid,))
    return get_conversation(cid)

