"""Data-driven clause-type classifier using CUAD exemplars.

Uses TF-IDF similarity against CUAD-labeled clause examples to classify
arbitrary contract clauses into one of 41 CUAD clause types. This is the
core data-driven modeling component: we learn what each clause type
"looks like" from the labeled dataset, then apply that model to new text.
"""

import re
from collections import defaultdict
from math import log, sqrt

from src.data_loader import CLAUSE_TYPES, get_clause_risk


class ClauseClassifier:
    """Classify clause text into CUAD clause types using TF-IDF similarity."""

    def __init__(self):
        self.exemplars = defaultdict(list)  # clause_type -> list of example texts
        self.idf = {}  # term -> inverse document frequency
        self.type_centroids = {}  # clause_type -> average TF-IDF vector
        self._fitted = False

    def fit(self, cuad_contracts):
        """Build the classifier from extracted CUAD contract data.

        Args:
            cuad_contracts: list of contract dicts from get_sample_contracts(),
                            each with a "clauses" list containing clause_type and text.
        """
        # Collect exemplars per clause type
        all_docs = []
        for contract in cuad_contracts:
            for clause in contract.get("clauses", []):
                ctype = clause["clause_type"]
                text = clause["text"]
                self.exemplars[ctype].append(text)
                all_docs.append(text)

        if not all_docs:
            return

        # Build IDF from all clause texts
        n_docs = len(all_docs)
        doc_freq = defaultdict(int)
        for doc in all_docs:
            tokens = set(self._tokenize(doc))
            for token in tokens:
                doc_freq[token] += 1

        self.idf = {
            term: log(n_docs / (1 + df))
            for term, df in doc_freq.items()
        }

        # Build centroid TF-IDF vector per clause type
        for ctype, texts in self.exemplars.items():
            vectors = [self._tfidf(text) for text in texts]
            self.type_centroids[ctype] = self._average_vectors(vectors)

        self._fitted = True

    def classify(self, clause_text, top_k=3):
        """Classify a clause into CUAD types.

        Returns list of (clause_type, similarity_score, risk_level) tuples,
        sorted by similarity descending. Returns top_k matches.
        """
        if not self._fitted:
            return []

        query_vec = self._tfidf(clause_text)
        scores = []

        for ctype, centroid in self.type_centroids.items():
            sim = self._cosine_similarity(query_vec, centroid)
            if sim > 0.01:  # minimum threshold
                scores.append((ctype, sim, get_clause_risk(ctype)))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def get_exemplars(self, clause_type, n=3):
        """Get n example texts for a clause type from CUAD.

        Used for few-shot prompting: show the LLM real examples of
        what this clause type looks like in actual contracts.
        """
        examples = self.exemplars.get(clause_type, [])
        # Return shortest examples (most focused/readable)
        examples = sorted(examples, key=len)
        return examples[:n]

    def get_statistics(self):
        """Return dataset statistics for the data analysis component."""
        stats = {
            "total_exemplars": sum(len(v) for v in self.exemplars.values()),
            "clause_types_with_data": len(self.exemplars),
            "exemplars_per_type": {
                k: len(v) for k, v in sorted(
                    self.exemplars.items(), key=lambda x: len(x[1]), reverse=True
                )
            },
            "risk_distribution": {"high": 0, "medium": 0, "low": 0},
        }
        for ctype in self.exemplars:
            risk = get_clause_risk(ctype)
            stats["risk_distribution"][risk] += len(self.exemplars[ctype])
        return stats

    def _tokenize(self, text):
        """Simple whitespace + punctuation tokenizer."""
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        tokens = text.split()
        # Remove very short tokens and common stopwords
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "is", "are", "was", "were",
            "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "shall",
            "this", "that", "these", "those", "it", "its", "not", "no",
            "any", "all", "each", "every", "such", "as", "if", "than",
        }
        return [t for t in tokens if len(t) > 2 and t not in stopwords]

    def _tfidf(self, text):
        """Compute TF-IDF vector for a text."""
        tokens = self._tokenize(text)
        if not tokens:
            return {}
        tf = defaultdict(int)
        for token in tokens:
            tf[token] += 1
        max_tf = max(tf.values())
        return {
            term: (count / max_tf) * self.idf.get(term, 0)
            for term, count in tf.items()
        }

    def _cosine_similarity(self, vec_a, vec_b):
        """Compute cosine similarity between two sparse vectors (dicts)."""
        common = set(vec_a.keys()) & set(vec_b.keys())
        if not common:
            return 0.0
        dot = sum(vec_a[k] * vec_b[k] for k in common)
        norm_a = sqrt(sum(v * v for v in vec_a.values()))
        norm_b = sqrt(sum(v * v for v in vec_b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _average_vectors(self, vectors):
        """Compute element-wise average of sparse vectors."""
        if not vectors:
            return {}
        combined = defaultdict(float)
        for vec in vectors:
            for term, val in vec.items():
                combined[term] += val
        n = len(vectors)
        return {term: val / n for term, val in combined.items()}
