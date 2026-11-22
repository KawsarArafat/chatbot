import argparse
from app.services import get_collection,retrieve
def main():
    p=argparse.ArgumentParser();p.add_argument('--document-id',required=True);p.add_argument('--question',action='append',required=True);a=p.parse_args()
    got=get_collection().get(where={'document_id':a.document_id},include=['documents','metadatas'])
    rows=[{'id':i,'text':t,'metadata':m} for i,t,m in zip(got['ids'],got['documents'],got['metadatas'])]
    for q in a.question:
        print(f'\nQUESTION: {q}')
        for x in retrieve(q,[a.document_id],rows)[:5]:print(f"  p.{x['metadata']['page_number']} {x['text'][:220]}")
if __name__=='__main__':main()

