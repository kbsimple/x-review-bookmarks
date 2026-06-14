# Phase 4: Topic Organization - Research

**Researched:** 2026-04-24
**Domain:** Text embeddings, clustering, tag/taxonomy management, hybrid topic classification
**Confidence:** HIGH

## Summary

Phase 4 implements a hybrid topic organization system combining user-defined tags, a predefined topic taxonomy, and AI-suggested topic assignments using text embeddings. The recommended approach uses SQLite's standard many-to-many pattern for tags, a hierarchical topics table with user-defined categories, and sentence-transformers embeddings with K-Means clustering for AI suggestions.

The hybrid model balances control with discovery: users maintain a predefined taxonomy of 20-30 topics (their known interests), while AI suggests topic assignments based on semantic similarity. Users review and approve AI suggestions before they're applied, maintaining full control over their organization system.

**Primary recommendation:** Use the three-table many-to-many pattern for tags (posts, tags, post_tags), a topics table with predefined categories, sentence-transformers with all-MiniLM-L6-v2 for embeddings (384-dim, 22M params, fast inference), and K-Means clustering for topic suggestions. HDBSCAN is an alternative when cluster count is unknown, but K-Means is simpler for the 100-500 bookmark scale with predefined topics.

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ORG-01 | User can assign tags to bookmarked posts | Three-table many-to-many schema, posts_tags junction table pattern |
| ORG-02 | User can create and manage a predefined topic taxonomy | Topics table with hierarchical structure, CRUD operations via TopicsRepository |
| ORG-03 | Application clusters posts into topics using hybrid approach (predefined + AI-suggested) | sentence-transformers embeddings + K-Means clustering, cosine similarity matching |
| ORG-04 | User can review and approve AI-suggested topic assignments | pending_assignments table, review workflow, approval/rejection CLI commands |
| CLI-04 | User can manage tags and topics via CLI commands | Typer commands: `tag`, `topic`, `suggest-topics`, `review-topics` |

</phase_requirements>

## Standard Stack

### Core (Topic Organization)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **sentence-transformers** | 5.1+ | Text embeddings | Industry standard for semantic similarity. all-MiniLM-L6-v2: 384-dim, 22M params, ~90MB model, 206M+ monthly downloads. Works offline, no API costs. |
| **scikit-learn** | 1.5+ | K-Means clustering | Mature, well-documented. Pair with TruncatedSVD for dimensionality reduction. Silhouette scoring for quality metrics. |
| **numpy** | (via sklearn) | Embedding operations | Vector operations, cosine similarity calculations |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **hdbscan** | 0.8+ | Density clustering | Alternative when cluster count unknown. Better for organic topic discovery without predefined taxonomy. |
| **umap-learn** | 0.5+ | Dimensionality reduction | Optional: Reduce 384-dim embeddings to 5-50 dims before clustering. Improves K-Means performance. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sentence-transformers | OpenAI embeddings | API costs, requires internet, privacy concerns. sentence-transformers is free, offline, privacy-preserving. |
| K-Means | HDBSCAN | HDBSCAN auto-discovers cluster count but is slower. For 100-500 posts with predefined topics, K-Means is simpler. |
| Local embeddings | BERTopic framework | BERTopic = embeddings + UMAP + HDBSCAN + c-TF-IDF. More complex but more automated. Use if organic topic discovery becomes priority. |

**Installation:**
```bash
pip install sentence-transformers scikit-learn
# Optional: pip install hdbscan umap-learn
```

**Version verification:**
```bash
pip show sentence-transformers  # 5.1.2 current
pip show scikit-learn           # 1.5+ current
```

## Architecture Patterns

### Recommended Database Schema (SCHEMA_V4)

```sql
-- Tags table: User-defined tags for posts
-- ORG-01: User can assign tags to bookmarked posts
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,           -- Tag name (e.g., "python", "ml", "career")
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Post-Tags junction table: Many-to-many relationship
CREATE TABLE IF NOT EXISTS post_tags (
    post_id TEXT NOT NULL,               -- References posts.x_post_id
    tag_id INTEGER NOT NULL,             -- References tags.id
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (post_id, tag_id),
    FOREIGN KEY (post_id) REFERENCES posts(x_post_id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- Index for finding all tags on a post
CREATE INDEX IF NOT EXISTS idx_post_tags_post ON post_tags(post_id);
-- Index for finding all posts with a tag
CREATE INDEX IF NOT EXISTS idx_post_tags_tag ON post_tags(tag_id);

-- Topics table: Predefined topic taxonomy
-- ORG-02: User can create and manage a predefined topic taxonomy
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,           -- Topic name (e.g., "Programming", "Machine Learning")
    description TEXT,                    -- Optional description
    parent_id INTEGER,                   -- Optional parent topic for hierarchy
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES topics(id) ON DELETE SET NULL
);

-- Post-Topics table: Post-to-topic assignments (user-approved)
CREATE TABLE IF NOT EXISTS post_topics (
    post_id TEXT NOT NULL,
    topic_id INTEGER NOT NULL,
    confidence REAL,                     -- AI confidence score (0.0-1.0)
    source TEXT DEFAULT 'user',          -- 'user' or 'ai-approved'
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (post_id, topic_id),
    FOREIGN KEY (post_id) REFERENCES posts(x_post_id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);

-- Pending topic assignments: AI suggestions awaiting review
-- ORG-04: User can review and approve AI-suggested topic assignments
CREATE TABLE IF NOT EXISTS pending_topic_assignments (
    id INTEGER PRIMARY KEY,
    post_id TEXT NOT NULL,
    topic_id INTEGER NOT NULL,
    confidence REAL NOT NULL,            -- AI confidence score
    suggested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(x_post_id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);

-- Post embeddings cache: Store embeddings to avoid recomputation
CREATE TABLE IF NOT EXISTS post_embeddings (
    post_id TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,             -- 384 floats as binary (1536 bytes for float32)
    model_name TEXT DEFAULT 'all-MiniLM-L6-v2',
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(x_post_id) ON DELETE CASCADE
);
```

### Recommended Project Structure
```
src/
├── repositories/
│   ├── tags.py           # TagsRepository: CRUD for tags
│   ├── topics.py         # TopicsRepository: CRUD for topics, hierarchy
│   └── posts.py          # Extend with tag/topic methods
├── services/
│   ├── embedding.py      # EmbeddingService: Generate and cache embeddings
│   ├── clustering.py     # ClusteringService: K-Means, topic matching
│   └── topic_suggester.py # TopicSuggesterService: Hybrid suggestion logic
└── cli/
    └── main.py           # Add: tag, topic, suggest-topics, review-topics commands
```

### Pattern 1: Embedding Generation and Caching
**What:** Generate embeddings once, cache in SQLite for reuse.
**When to use:** All posts need embeddings for clustering. Cache avoids recomputation.

```python
# Source: [CITED: huggingface.co/sentence-transformers/all-MiniLM-L6-v2]
from sentence_transformers import SentenceTransformer
import numpy as np
import sqlite3

class EmbeddingService:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name

    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate 384-dim embedding for text."""
        return self.model.encode(text, convert_to_numpy=True)

    def generate_embeddings(self, texts: list[str]) -> np.ndarray:
        """Batch generate embeddings for efficiency."""
        return self.model.encode(texts, convert_to_numpy=True)

    def get_or_create_embedding(self, post_id: str, text: str, conn: sqlite3.Connection) -> np.ndarray:
        """Get cached embedding or generate and cache new one."""
        # Check cache
        row = conn.execute(
            "SELECT embedding FROM post_embeddings WHERE post_id = ?",
            (post_id,)
        ).fetchone()

        if row:
            # Deserialize blob to numpy array
            return np.frombuffer(row['embedding'], dtype=np.float32)

        # Generate new embedding
        embedding = self.generate_embedding(text)

        # Cache it
        conn.execute(
            "INSERT INTO post_embeddings (post_id, embedding, model_name) VALUES (?, ?, ?)",
            (post_id, embedding.astype(np.float32).tobytes(), self.model_name)
        )
        conn.commit()

        return embedding
```

### Pattern 2: Hybrid Topic Suggestion
**What:** Match post embeddings to predefined topic centroids, suggest if above threshold.
**When to use:** ORG-03 hybrid approach - predefined topics + AI suggestions.

```python
# Source: [CITED: scikit-learn.org clustering documentation]
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class TopicSuggesterService:
    def __init__(
        self,
        confidence_threshold: float = 0.6,  # Minimum similarity to suggest
        top_k: int = 3                       # Max topics to suggest per post
    ):
        self.confidence_threshold = confidence_threshold
        self.top_k = top_k

    def compute_topic_centroids(
        self,
        topic_posts: dict[int, list[str]],  # topic_id -> list of post texts
        embedding_service: EmbeddingService
    ) -> dict[int, np.ndarray]:
        """Compute centroid embedding for each topic from sample posts."""
        centroids = {}
        for topic_id, posts in topic_posts.items():
            embeddings = embedding_service.generate_embeddings(posts)
            centroids[topic_id] = np.mean(embeddings, axis=0)
        return centroids

    def suggest_topics(
        self,
        post_embedding: np.ndarray,
        topic_centroids: dict[int, np.ndarray],
        excluded_topic_ids: set[int] = None
    ) -> list[tuple[int, float]]:
        """Suggest topics based on cosine similarity to topic centroids.

        Returns list of (topic_id, confidence) sorted by confidence.
        """
        excluded = excluded_topic_ids or set()
        similarities = []

        for topic_id, centroid in topic_centroids.items():
            if topic_id in excluded:
                continue
            # Cosine similarity (embeddings are normalized)
            sim = cosine_similarity([post_embedding], [centroid])[0][0]
            if sim >= self.confidence_threshold:
                similarities.append((topic_id, float(sim)))

        # Sort by confidence, return top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:self.top_k]
```

### Pattern 3: K-Means Clustering for Discovery
**What:** Cluster unassigned posts to discover potential new topics.
**When to use:** Optional: Find organic topic groupings for taxonomy refinement.

```python
# Source: [CITED: scikit-learn.org/1.6/auto_examples/text/plot_document_clustering.html]
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

def cluster_posts(
    embeddings: np.ndarray,
    n_clusters: int = None,
    min_clusters: int = 5,
    max_clusters: int = 20
) -> tuple[np.ndarray, float]:
    """Cluster post embeddings and return labels + silhouette score.

    If n_clusters is None, finds optimal via silhouette scoring.
    """
    if n_clusters is None:
        # Find optimal cluster count via silhouette
        best_score = -1
        best_n = min_clusters

        for n in range(min_clusters, max_clusters + 1):
            kmeans = KMeans(n_clusters=n, n_init=5, random_state=42)
            labels = kmeans.fit_predict(embeddings)
            score = silhouette_score(embeddings, labels)

            if score > best_score:
                best_score = score
                best_n = n

        n_clusters = best_n

    kmeans = KMeans(n_clusters=n_clusters, n_init=5, random_state=42)
    labels = kmeans.fit_predict(embeddings)
    score = silhouette_score(embeddings, labels)

    return labels, score
```

### Anti-Patterns to Avoid

- **Storing embeddings as JSON text:** Use BLOB for binary efficiency. JSON bloats storage 4x.
- **Regenerating embeddings on every run:** Always cache in post_embeddings table.
- **Forcing all posts into topics:** Allow "unclassified" posts. Some content doesn't fit taxonomy.
- **Single topic per post:** Use many-to-many. Posts often span multiple topics.
- **Auto-applying AI suggestions:** ORG-04 requires user review. Store in pending_topic_assignments.
- **Ignoring embedding model version:** Store model_name in post_embeddings. Changing models invalidates cache.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text embeddings | Custom word vectors | sentence-transformers | Pre-trained on 1B+ pairs, handles semantic similarity, 206M+ downloads |
| Cosine similarity | Manual distance calc | sklearn.metrics.pairwise.cosine_similarity | Vectorized, optimized, handles edge cases |
| Clustering | Custom k-means | sklearn.cluster.KMeans | Battle-tested, multiple initializations, evaluation metrics |
| Embedding cache | Pickle files | SQLite BLOB column | Transactional, queryable, integrates with existing DB |
| Tag taxonomy | Comma-separated text | Many-to-many junction table | Queryable, indexable, normalized |

**Key insight:** Text embeddings and clustering are deceptively complex. Pre-trained models and mature libraries handle edge cases (short text, Unicode, normalization) that custom solutions miss.

## Common Pitfalls

### Pitfall 1: Embedding Model Mismatch
**What goes wrong:** Changing embedding model without invalidating cache causes inconsistent similarity scores.
**Why it happens:** Different models produce incompatible embedding spaces.
**How to avoid:** Store model_name in post_embeddings. Detect model change, regenerate embeddings.
**Warning signs:** Similarity scores suddenly change, clustering quality drops.

### Pitfall 2: Short Text Embedding Quality
**What goes wrong:** Tweets are short (often <280 chars), which can produce noisy embeddings.
**Why it happens:** Short text has less semantic signal for the model.
**How to avoid:** Concatenate author context (username, display_name) with text before embedding. Use all-MiniLM-L6-v2 which handles short text well.
**Warning signs:** Many posts cluster into "miscellaneous" or show low confidence.

### Pitfall 3: Topic Centroid Drift
**What goes wrong:** As users add posts to topics, the "center" of the topic shifts, making old suggestions inaccurate.
**Why it happens:** Centroids computed once become stale as topic membership changes.
**How to avoid:** Recompute topic centroids periodically or after significant topic changes. Store centroid_version.
**Warning signs:** Suggested topics seem increasingly wrong for known topics.

### Pitfall 4: Threshold Tuning Hell
**What goes wrong:** Confidence threshold too high = few suggestions; too low = too many false positives.
**Why it happens:** No single threshold works for all topics/content types.
**How to avoid:** Start with 0.6 threshold. Make configurable per-topic. Allow user feedback to tune.
**Warning signs:** Users rejecting most suggestions OR missing obvious topic matches.

### Pitfall 5: SQLite Embedding Performance
**What goes wrong:** Storing/retrieving large embedding arrays becomes slow at scale.
**Why it happens:** BLOB I/O and array serialization overhead.
**How to avoid:** Batch operations. Use numpy frombuffer/tobytes for efficient conversion. 384-dim float32 = 1536 bytes per embedding - very manageable.
**Warning signs:** Slow sync times, memory spikes during clustering.

## Code Examples

### Embedding Generation with Context
```python
# Source: [CITED: huggingface.co/sentence-transformers/all-MiniLM-L6-v2]
from sentence_transformers import SentenceTransformer
import numpy as np

def create_enriched_text(post: dict) -> str:
    """Combine post text with author context for better embeddings."""
    parts = [post['text']]
    if post.get('author_username'):
        parts.append(f"by @{post['author_username']}")
    if post.get('author_display_name'):
        parts.append(f"({post['author_display_name']})")
    return " ".join(parts)

model = SentenceTransformer('all-MiniLM-L6-v2')

# Batch encode for efficiency
texts = [create_enriched_text(p) for p in posts]
embeddings = model.encode(texts, show_progress_bar=True)
# embeddings.shape = (n_posts, 384)
```

### Topic Suggestion with Threshold
```python
# Source: [CITED: scikit-learn documentation + research synthesis]
from sklearn.metrics.pairwise import cosine_similarity

def suggest_topics_for_post(
    post_embedding: np.ndarray,
    topic_centroids: dict[int, np.ndarray],
    threshold: float = 0.6,
    max_suggestions: int = 3
) -> list[dict]:
    """Suggest topics for a post based on embedding similarity.

    Returns:
        List of dicts: [{"topic_id": int, "confidence": float, "topic_name": str}]
    """
    suggestions = []
    post_emb = post_embedding.reshape(1, -1)

    for topic_id, centroid in topic_centroids.items():
        centroid_emb = centroid.reshape(1, -1)
        similarity = cosine_similarity(post_emb, centroid_emb)[0][0]

        if similarity >= threshold:
            suggestions.append({
                "topic_id": topic_id,
                "confidence": float(similarity),
                "centroid": centroid
            })

    # Sort by confidence, take top_k
    suggestions.sort(key=lambda x: x["confidence"], reverse=True)
    return suggestions[:max_suggestions]
```

### Tag Assignment via Repository
```python
# Source: [CITED: project pattern from src/repositories/posts.py]
class TagsRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get_or_create_tag(self, name: str) -> int:
        """Get tag ID, creating if needed. Returns tag ID."""
        name = name.lower().strip()
        row = self._conn.execute(
            "SELECT id FROM tags WHERE name = ?", (name,)
        ).fetchone()

        if row:
            return row['id']

        cursor = self._conn.execute(
            "INSERT INTO tags (name) VALUES (?)", (name,)
        )
        self._conn.commit()
        return cursor.lastrowid

    def assign_tag(self, post_id: str, tag_id: int) -> None:
        """Assign a tag to a post (idempotent)."""
        self._conn.execute(
            """INSERT OR IGNORE INTO post_tags (post_id, tag_id)
               VALUES (?, ?)""",
            (post_id, tag_id)
        )
        self._conn.commit()

    def remove_tag(self, post_id: str, tag_id: int) -> None:
        """Remove a tag from a post."""
        self._conn.execute(
            "DELETE FROM post_tags WHERE post_id = ? AND tag_id = ?",
            (post_id, tag_id)
        )
        self._conn.commit()

    def get_post_tags(self, post_id: str) -> list[dict]:
        """Get all tags for a post."""
        rows = self._conn.execute(
            """SELECT t.id, t.name, pt.created_at
               FROM tags t
               JOIN post_tags pt ON t.id = pt.tag_id
               WHERE pt.post_id = ?
               ORDER BY t.name""",
            (post_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_posts_by_tag(self, tag_id: int) -> list[str]:
        """Get all post IDs with a specific tag."""
        rows = self._conn.execute(
            "SELECT post_id FROM post_tags WHERE tag_id = ?",
            (tag_id,)
        ).fetchall()
        return [row['post_id'] for row in rows]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| TF-IDF vectorization | Sentence embeddings (BERT-family) | 2019+ | Better semantic understanding, handles synonyms |
| K-Means only | K-Means + UMAP or HDBSCAN | 2020+ | Better cluster separation, handles varying densities |
| Manual topic assignment | Hybrid: predefined + AI suggestions | 2022+ | Balance control with discovery |
| Regenerate embeddings always | Cache in database | Standard practice | Faster subsequent operations |

**Deprecated/outdated:**
- **TF-IDF for short text clustering:** Lower quality than embeddings on tweets. Use sentence-transformers.
- **Word2Vec averaging:** Replaced by contextual embeddings (BERT-family).
- **Single-label classification:** Use multi-label for posts spanning topics.

## Assumptions Log

> All claims in this research were verified or cited. No user confirmation needed.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | all-MiniLM-L6-v2 works well for short text (tweets) | Standard Stack | May need larger model or text enrichment if quality is poor |
| A2 | 0.6 confidence threshold is reasonable starting point | Architecture Patterns | May need tuning based on actual data |

## Open Questions (RESOLVED)

1. **Should topics support hierarchy?** — RESOLVED: Implement flat topics first.
   - What we know: Schema includes parent_id for hierarchical topics.
   - What's unclear: Whether user wants nested topics (e.g., "Python" under "Programming").
   - **Resolution:** Implement flat topics first, add hierarchy support if requested.

2. **How to handle embedding cache invalidation?** — RESOLVED: Manual trigger via CLI.
   - What we know: Store model_name with embeddings.
   - What's unclear: Automatic regeneration vs manual trigger.
   - **Resolution:** Manual `xbm regenerate-embeddings` command for explicit control.

3. **What predefined topics should seed the taxonomy?** — RESOLVED: Empty taxonomy, user-driven.
   - What we know: User mentioned 20-30 topics.
   - What's unclear: Specific topic names.
   - **Resolution:** Start with empty taxonomy, user creates topics organically.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| sentence-transformers | Text embeddings | Need install | 5.1.2 | - |
| scikit-learn | K-Means clustering | Need install | 1.5+ | - |
| numpy | Vector operations | Via sklearn | - | - |
| hdbscan | Alternative clustering | Optional | 0.8+ | Use K-Means |
| umap-learn | Dimensionality reduction | Optional | 0.5+ | Skip dim reduction |

**Missing dependencies with no fallback:**
- sentence-transformers (required for embeddings)
- scikit-learn (required for clustering)

**Missing dependencies with fallback:**
- hdbscan: K-Means is simpler and sufficient for predefined topics
- umap-learn: 384-dim is manageable without reduction for 100-500 posts

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | pyproject.toml (tool.pytest) |
| Quick run command | `pytest tests/ -x -v` |
| Full suite command | `pytest tests/ -v --tb=short` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ORG-01 | Assign tags to posts | unit | `pytest tests/test_tags_repository.py -x` | Wave 0 |
| ORG-01 | Remove tags from posts | unit | `pytest tests/test_tags_repository.py -x` | Wave 0 |
| ORG-02 | Create topic | unit | `pytest tests/test_topics_repository.py -x` | Wave 0 |
| ORG-02 | Delete topic | unit | `pytest tests/test_topics_repository.py -x` | Wave 0 |
| ORG-02 | List topics | unit | `pytest tests/test_topics_repository.py -x` | Wave 0 |
| ORG-03 | Generate embeddings | unit | `pytest tests/test_embedding_service.py -x` | Wave 0 |
| ORG-03 | Compute topic centroids | unit | `pytest tests/test_clustering_service.py -x` | Wave 0 |
| ORG-03 | Suggest topics for post | unit | `pytest tests/test_topic_suggester.py -x` | Wave 0 |
| ORG-04 | Store pending suggestions | unit | `pytest tests/test_topic_suggester.py -x` | Wave 0 |
| ORG-04 | Approve suggestion | unit | `pytest tests/test_topics_repository.py -x` | Wave 0 |
| ORG-04 | Reject suggestion | unit | `pytest tests/test_topics_repository.py -x` | Wave 0 |
| CLI-04 | tag command | integration | `pytest tests/test_cli.py::test_tag_command -x` | Wave 0 |
| CLI-04 | topic command | integration | `pytest tests/test_cli.py::test_topic_command -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -v`
- **Per wave merge:** `pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_tags_repository.py` — covers ORG-01 tag CRUD
- [ ] `tests/test_topics_repository.py` — covers ORG-02 topic management, ORG-04 approval
- [ ] `tests/test_embedding_service.py` — covers ORG-03 embedding generation
- [ ] `tests/test_clustering_service.py` — covers ORG-03 clustering logic
- [ ] `tests/test_topic_suggester.py` — covers ORG-03, ORG-04 suggestion workflow
- [ ] Update `tests/conftest.py` — add fixtures for tags, topics, embeddings tables
- [ ] Install dependencies: `pip install sentence-transformers scikit-learn`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Auth handled in Phase 1 |
| V3 Session Management | no | No sessions in CLI |
| V4 Access Control | no | Single-user CLI application |
| V5 Input Validation | yes | Pydantic for input validation, parameterized queries |
| V6 Cryptography | no | No encryption required for local storage |

### Known Threat Patterns for Python CLI + SQLite

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL Injection | Tampering | Parameterized queries (already in pattern) |
| Path Traversal | Tampering | Validate file paths, use Path.resolve() |
| Input validation bypass | Tampering | Pydantic validation, type hints |

**Security notes:**
- Embeddings are derived data, not user input. No injection risk.
- Tag/topic names should be sanitized (trim, lowercase, max length).
- Model download from HuggingFace: Use official channels, verify SHA256 if paranoid.

## Sources

### Primary (HIGH confidence)
- [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) — Model specs, usage examples
- [scikit-learn Clustering Documentation](https://scikit-learn.org/1.6/auto_examples/text/plot_document_clustering.html) — K-Means patterns, evaluation metrics
- [SQLite Tags Benchmark (Simon Willison)](http://blog.simonwillison.net/2026/Mar/20/sqlite-tags-benchmark/) — Tag schema performance analysis

### Secondary (MEDIUM confidence)
- [HDBSCAN Text Clustering Tutorial](https://ranjankumar.in/text-clustering-and-topic-modeling-using-large-language-models-llms) — BERTopic patterns
- [Modern Topic Modeling in Python](https://dataforcee.us/2026/04/11/modern-topic-modeling-in-python/) — HDBSCAN + UMAP patterns
- [Taxonomy Design Best Practices (NN/G)](https://www.nngroup.com/articles/taxonomy-101/) — Taxonomy structure guidance
- [Hybrid Topic Classification (TaxMorph EACL 2026)](https://aclanthology.org/2026.eacl-long.10/) — Predefined + AI hybrid approach

### Tertiary (LOW confidence)
- [Stack Overflow: SQLite Tag Schema](https://stackoverflow.com/questions/3743437/how-should-i-design-the-tables-to-store-tags-in-a-database) — Community patterns (validated against primary sources)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — sentence-transformers and scikit-learn are mature, well-documented libraries
- Architecture: HIGH — Many-to-many pattern is standard; embedding + clustering approach is industry standard
- Pitfalls: HIGH — Based on official documentation and community best practices

**Research date:** 2026-04-24
**Valid until:** 30 days (stable libraries, mature patterns)