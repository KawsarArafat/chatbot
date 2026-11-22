import numpy as np
import fitz
from app import services
from app.services import assemble,bm25,build_chunks,extract_pdf
class Embed:
    def encode(self,texts,normalize_embeddings=True):return np.tile(np.array([[1.,0.]]),(len(texts),1))
class Cross:
    def predict(self,pairs):return [float(len(text)) for _,text in pairs]
def rows():return [{'id':'a','text':'Admission needs academic qualifications.','metadata':{'document_id':'d','parent_chunk_id':'p1','filename':'guide.pdf','page_number':4,'section_title':'Eligibility'}},{'id':'b','text':'Campus housing has residence halls.','metadata':{'document_id':'d','parent_chunk_id':'p2','filename':'guide.pdf','page_number':8,'section_title':'Housing'}}]
def test_pdf_page_extraction(tmp_path):
    d=fitz.open();d.new_page().insert_text((72,72),'First page');d.new_page().insert_text((72,72),'Second page');p=tmp_path/'a.pdf';p.write_bytes(d.tobytes());d.close();meta,pages=extract_pdf(p);assert meta['page_count']==2 and pages[1]['page_number']==2
def test_chunk_parent_child_page_links():
    ps,cs=build_chunks([{'page_number':2,'text':' '.join(['A sentence about topic.']*70)}],Embed());ids={p['id'] for p in ps};assert cs and all(c['parent_id'] in ids and c['page_number']==2 for c in cs)
def test_embeddings_normalize(monkeypatch):
    class E:
        def encode(self,texts,normalize_embeddings):self.norm=normalize_embeddings;return [[1.,0.]]
    e=E();monkeypatch.setattr(services,'get_embedder',lambda:e);services.embed(['q']);assert e.norm
def test_chroma_metadata_storage(monkeypatch):
    class C:
        def add(self,**kwargs):self.data=kwargs
    c=C();monkeypatch.setattr(services,'get_collection',lambda:c);monkeypatch.setattr(services,'embed',lambda _: [[.1]])
    services.add_document('d','guide.pdf',[{'id':'c','parent_id':'p','text':'chunk','page_number':4,'section_title':'Rules'}]);assert c.data['metadatas'][0]['parent_chunk_id']=='p' and c.data['metadatas'][0]['page_number']==4
def test_bm25_keyword_ranking_and_empty():assert bm25('academic qualifications',rows(),2)[0][0]=='a' and bm25('x',[],2)==[]
def test_hybrid_reciprocal_rank_fusion(monkeypatch):
    monkeypatch.setattr(services,'embed',lambda _: [[.1,.2]]);monkeypatch.setattr(services,'query',lambda *a:{'ids':[['a','b']],'distances':[[.1,.2]]});assert services.retrieve('academic qualifications',['d'],rows())[0]['id']=='a'
def test_cross_encoder_reranking(monkeypatch):monkeypatch.setattr(services,'_model',lambda:Cross());assert services.rerank('q',rows(),2)[0]['id']=='a'
def test_query_rewrite_uses_history(monkeypatch):monkeypatch.setattr(services,'complete',lambda messages,temp:'Eligibility rules');assert services.rewrite_query('Explain that','','Eligibility discussion')=='Eligibility rules'
def test_clear_query_skips_rewrite(monkeypatch):
    monkeypatch.setattr(services,'complete',lambda *args:1/0);assert services.rewrite_query('What are the academic admission requirements?','','').startswith('What are')
def test_summary_update(monkeypatch):monkeypatch.setattr(services,'complete',lambda *args:'Page 4 eligibility');assert 'page 4' in services.update_summary('','new').lower()
def test_context_sources_and_parent_dedupe():
    r=rows();r.append({**r[0],'id':'c'});text=assemble('Q','summary','recent',r)[-1]['content'];assert 'guide.pdf | Page 4 | Section Eligibility' in text and text.count('Source: guide.pdf | Page 4')==1
