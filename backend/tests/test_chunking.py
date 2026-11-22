import unittest
from app.services import build_chunks
class FakeEmbedder:
    def encode(self,texts,normalize_embeddings=True): return [[1.0,0.0] for _ in texts]
class ChunkTests(unittest.TestCase):
    def test_parent_child_and_page_metadata(self):
        parents,children=build_chunks([{'page_number':3,'text':' '.join(['A long sentence about a topic.']*70)}],FakeEmbedder())
        self.assertTrue(parents and children); pids={p['id'] for p in parents}
        self.assertTrue(all(c['parent_id'] in pids and c['page_number']==3 for c in children))
if __name__=='__main__': unittest.main()

