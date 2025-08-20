# nlp.py
import os
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import faiss

class NCOIndexer:
    def __init__(self, index_dir: str, model_name: str):
        os.makedirs(index_dir, exist_ok=True)
        self.index_dir = index_dir
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.id_map: List[str] = []

    def _index_path(self):
        return os.path.join(self.index_dir, 'nco.faiss')

    def _ids_path(self):
        return os.path.join(self.index_dir, 'nco_ids.npy')

    def save(self):
        if self.index is None:
            return
        faiss.write_index(self.index, self._index_path())
        np.save(self._ids_path(), np.array(self.id_map, dtype=object))

    def load(self) -> bool:
        if os.path.exists(self._index_path()) and os.path.exists(self._ids_path()):
            self.index = faiss.read_index(self._index_path())
            self.id_map = np.load(self._ids_path(), allow_pickle=True).tolist()
            return True
        return False

    def build(self, items: List[Dict[str, Any]]):
        texts = []
        self.id_map = []
        for it in items:
            blob = f"{it.get('title','')} — {it.get('description','')} — {it.get('code','')} — {it.get('path','')}"
            texts.append(blob)
            self.id_map.append(str(it['_id']))
        if not texts:
            self.index = None
            return
        emb = self.model.encode(texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
        d = emb.shape[1]
        self.index = faiss.IndexFlatIP(d)  # cosine via normalized inner product
        self.index.add(emb.astype('float32'))
        self.save()

    def search(self, queries: List[str], top_k: int = 5):
        if self.index is None and not self.load():
            raise RuntimeError('Index not built yet')
        q_emb = self.model.encode(queries, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
        scores, idxs = self.index.search(q_emb.astype('float32'), top_k)
        return scores, idxs
