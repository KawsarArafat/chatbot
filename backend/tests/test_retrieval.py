import unittest
from app.services import bm25
from app.services import assemble
class RetrievalTests(unittest.TestCase):
    def setUp(self): self.records=[{'id':'a','text':'Admission applicants need academic qualifications.','metadata':{'document_id':'d','parent_chunk_id':'p1','filename':'guide.pdf','page_number':4,'section_title':'Eligibility'}},{'id':'b','text':'Campus housing includes dining and residence halls.','metadata':{'document_id':'d','parent_chunk_id':'p2','filename':'guide.pdf','page_number':8,'section_title':'Housing'}}]
    def test_bm25_prefers_exact_terms(self): self.assertEqual(bm25('academic qualifications',self.records,2)[0][0],'a')
    def test_empty_bm25(self): self.assertEqual(bm25('anything',[],5),[])
    def test_citation_metadata_in_context(self): self.assertIn('guide.pdf | Page 4 | Section Eligibility',assemble('Question','','',self.records[:1])[-1]['content'])
    def test_context_deduplicates_parent(self):
        dup={**self.records[0],'id':'c'}; prompt=assemble('Question','','',[self.records[0],dup])
        self.assertEqual(prompt[-1]['content'].count('Source: guide.pdf'),1)
if __name__=='__main__': unittest.main()

