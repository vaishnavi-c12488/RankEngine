# RankEngine — Evaluation Report

## 1. Objective

Evaluate RankEngine's lexical baseline, dense bi-encoder baseline, and
LambdaMART reranker using the ESCI product-search dataset.

## 2. Relevance mapping and metrics

Graded relevance mapping:
- Exact (E): 3
- Substitute (S): 2
- Complement (C): 1
- Irrelevant (I): 0

Binary relevance threshold for MRR and Precision@5: relevance >= 3
(NDCG@10 uses graded relevance).

Metrics:
- NDCG@10: ranking quality using graded relevance.
- MRR: reciprocal rank of the first result meeting the binary threshold.
- Precision@5: fraction of the top five results meeting the threshold.

## 3. Official test judged-candidate evaluation

The existing evaluation covers 14,496 query groups and ranks only products
with official judgments for each query. It does not measure full-catalog
retrieval.

| Metric | BM25 | LambdaMART |
|---|---:|---:|
| NDCG@10 | 0.767478 | 0.787291 |
| MRR | 0.754351 | 0.790934 |
| Precision@5 | 0.562983 | 0.587804 |
| Query groups | 14,496 | 14,496 |

LambdaMART outperformed BM25 on all three reported metrics in this
judged-candidate evaluation.

Source: `test_results.json`.

## 4. Three-ranker sampled evaluation

A reproducible sample of 500 query groups was selected with random seed 42.
All judged candidates for each selected query group were included, producing
11,415 judged rows.

| Metric | BM25 | Bi-encoder | LambdaMART |
|---|---:|---:|---:|
| NDCG@10 | 0.766719 | 0.767110 | 0.781731 |
| MRR | 0.759312 | 0.741147 | 0.794354 |
| Precision@5 | 0.551200 | 0.535200 | 0.573200 |
| Query groups | 500 | 500 | 500 |

Encoder: `sentence-transformers/all-MiniLM-L6-v2`.

LambdaMART achieved the highest scores for all three metrics in this sample.
The bi-encoder's NDCG@10 was close to BM25, while its MRR and Precision@5
were lower.

These are sampled judged-candidate ranking results. They must not be
interpreted as full-test results or as full-catalog retrieval performance.

Source: `three_ranker_sample_results.json`.

## 5. Evaluation methodology and limitations

- BM25 ranks judged candidates using lexical token matching.
- The bi-encoder ranks the same judged candidates by embedding similarity.
- LambdaMART ranks judged candidates using the trained learning-to-rank model.
- The full-test BM25/LambdaMART comparison and the sampled three-ranker
  comparison have different evaluation scopes and should not be compared
  as if they were the same experiment.
- MRR and Precision@5 use relevance >= 3 as the binary relevance threshold.
- NDCG@10 uses graded relevance.

### Outstanding evaluation requirement

Full-catalog dense retrieval Recall@K has not yet been measured. The current
deployment index is a development subset, not the complete 1,814,924-product
catalog. Therefore, no full-catalog Recall@K result is claimed in this report.

Before claiming complete retrieval evaluation, build or access a suitable
full-catalog index in an isolated location, measure Recall@K against the
official judgments, and document the chosen K values and per-locale results
where feasible.

## 6. Conclusion

The available ranking experiments show that LambdaMART improves the
reported ranking metrics over BM25 on both the official judged-candidate
evaluation and the reproducible 500-query sample. The bi-encoder sample
provides a baseline comparison, but it does not establish full-catalog
retrieval quality.

Full-catalog Recall@K remains outstanding. The results above are reported
with their evaluation scope so that the findings are reproducible and not
overstated.

## Final Verification Update

- Backend test suite: **49 passed**.
- Full-catalog source: 1,814,924 product-locale rows.
- Existing development index: 24,063 points.
- Three-ranker comparison: BM25, bi-encoder, and LambdaMART evaluated on a 500-query judged-candidate sample.
- BM25 vs. LambdaMART: LambdaMART improved NDCG@10 from 0.7675 to 0.7873 on the official judged-candidate test set.
- Development-subset retrieval Recall@10/50/100: 0.31% / 0.62% / 0.70% on a 500-query sample.
- Important limitation: only 66 of 5,416 exact-relevant product-locale pairs in the sample were present in the development index. The subset recall results must not be presented as full-catalog retrieval performance.
- Full-catalog Recall@K: pending. No full-catalog index build was performed.
- A separate 300-product index smoke test passed with 384-dimensional vectors; it is not the production index.

