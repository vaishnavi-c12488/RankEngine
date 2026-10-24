
"""Train and validate RankEngine's LightGBM LambdaMART ranker."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ranking.ltr_features import FEATURE_COLUMNS, build_ltr_features

TRAIN_FILE = PROJECT_ROOT / "data" / "processed" / "task1_train.parquet"
MODEL_DIR = PROJECT_ROOT / "ranking" / "model_registry"
MODEL_FILE = MODEL_DIR / "lambdamart.txt"
METADATA_FILE = MODEL_DIR / "lambdamart_metadata.json"

RANDOM_SEED = 42
VALIDATION_SIZE = 0.15
MAX_RELEVANCE = 3


def query_group_keys(frame: pd.DataFrame) -> pd.Series:
    """Create query groups that remain distinct across locales."""
    required = {"query_id", "product_locale"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing grouping columns: {sorted(missing)}")

    return (
        frame["query_id"].astype(str)
        + "::"
        + frame["product_locale"].astype(str)
    )


def prepare_grouped_data(
    frame: pd.DataFrame,
    features: pd.DataFrame,
    labels: pd.Series,
) -> tuple[pd.DataFrame, np.ndarray, list[int]]:
    """Sort rows by query group and generate LightGBM group sizes."""
    group_keys = query_group_keys(frame)

    order = np.argsort(group_keys.to_numpy(), kind="stable")
    sorted_features = features.iloc[order].reset_index(drop=True)
    sorted_labels = labels.iloc[order].to_numpy(dtype=np.int32)
    sorted_keys = group_keys.iloc[order].reset_index(drop=True)

    group_sizes = (
        sorted_keys.groupby(sorted_keys, sort=False)
        .size()
        .astype(int)
        .tolist()
    )

    if sum(group_sizes) != len(sorted_features):
        raise RuntimeError("Query group sizes do not match row count.")

    return sorted_features, sorted_labels, group_sizes


def mean_ndcg_at_10(
    model: lgb.LGBMRanker,
    features: pd.DataFrame,
    labels: np.ndarray,
    groups: list[int],
) -> float:
    """Calculate mean per-query NDCG@10 using exponential gain."""
    predictions = model.predict(features)
    scores = []
    offset = 0

    for group_size in groups:
        end = offset + group_size
        group_labels = labels[offset:end]
        group_scores = predictions[offset:end]

        ideal = np.sort(group_labels)[::-1][:10]
        ranked_indices = np.argsort(-group_scores, kind="stable")[:10]
        ranked = group_labels[ranked_indices]

        discounts = np.log2(np.arange(2, len(ranked) + 2))
        dcg = np.sum((np.power(2.0, ranked) - 1.0) / discounts)

        ideal_discounts = np.log2(np.arange(2, len(ideal) + 2))
        ideal_dcg = np.sum(
            (np.power(2.0, ideal) - 1.0) / ideal_discounts
        )

        if ideal_dcg > 0:
            scores.append(float(dcg / ideal_dcg))

        offset = end

    return float(np.mean(scores)) if scores else 0.0


def main() -> None:
    if not TRAIN_FILE.exists():
        raise FileNotFoundError(f"Training dataset not found: {TRAIN_FILE}")

    print(f"Loading training data: {TRAIN_FILE}", flush=True)
    frame = pd.read_parquet(TRAIN_FILE)

    required = {
        "query_id",
        "query",
        "product_locale",
        "relevance",
        "product_title",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Training data is missing columns: {sorted(missing)}")

    frame = frame.dropna(
        subset=["query_id", "query", "product_locale", "relevance"]
    ).copy()

    frame["relevance"] = pd.to_numeric(
        frame["relevance"], errors="raise"
    ).astype(int)

    if not frame["relevance"].between(0, MAX_RELEVANCE).all():
        raise ValueError("Relevance grades must be in the range 0–3.")

    # Keep only groups with at least two candidates for ranking.
    keys = query_group_keys(frame)
    group_counts = keys.value_counts()
    frame = frame.loc[
        keys.map(group_counts).ge(2)
    ].reset_index(drop=True)

    keys = query_group_keys(frame)
    unique_groups = keys.drop_duplicates().to_numpy()

    if len(unique_groups) < 2:
        raise ValueError("Not enough query groups to create a validation split.")

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=VALIDATION_SIZE,
        random_state=RANDOM_SEED,
    )
    train_indices, validation_indices = next(
        splitter.split(frame, groups=keys)
    )

    train_frame = frame.iloc[train_indices].reset_index(drop=True)
    validation_frame = frame.iloc[validation_indices].reset_index(drop=True)

    train_keys = set(query_group_keys(train_frame))
    validation_keys = set(query_group_keys(validation_frame))

    if train_keys & validation_keys:
        raise RuntimeError("Query leakage detected between train and validation.")

    print(f"Training rows: {len(train_frame):,}", flush=True)
    print(f"Validation rows: {len(validation_frame):,}", flush=True)
    print(f"Training query groups: {len(train_keys):,}", flush=True)
    print(f"Validation query groups: {len(validation_keys):,}", flush=True)

    print("Building training features...", flush=True)
    train_features = build_ltr_features(train_frame)

    print("Building validation features...", flush=True)
    validation_features = build_ltr_features(validation_frame)

    train_labels = train_frame["relevance"].astype(int)
    validation_labels = validation_frame["relevance"].astype(int)

    x_train, y_train, train_group_sizes = prepare_grouped_data(
        train_frame, train_features, train_labels
    )
    x_validation, y_validation, validation_group_sizes = prepare_grouped_data(
        validation_frame, validation_features, validation_labels
    )

    print("Training LambdaMART...", flush=True)

    ranker = lgb.LGBMRanker(
        objective="lambdarank",
        metric="ndcg",
        eval_at=[10],
        label_gain=[0, 1, 2, 3],
        n_estimators=500,
        learning_rate=0.05,
        num_leaves=31,
        max_depth=-1,
        min_child_samples=50,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        random_state=RANDOM_SEED,
        n_jobs=-1,
        verbosity=-1,
    )

    ranker.fit(
        x_train,
        y_train,
        group=train_group_sizes,
        eval_set=[(x_validation, y_validation)],
        eval_group=[validation_group_sizes],
        callbacks=[
            lgb.early_stopping(stopping_rounds=30, verbose=True),
            lgb.log_evaluation(period=25),
        ],
        feature_name=FEATURE_COLUMNS,
    )

    validation_ndcg = mean_ndcg_at_10(
        ranker,
        x_validation,
        y_validation,
        validation_group_sizes,
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    ranker.booster_.save_model(str(MODEL_FILE))

    metadata = {
        "model": "LightGBM LGBMRanker",
        "objective": "lambdarank",
        "model_file": str(MODEL_FILE.relative_to(PROJECT_ROOT)),
        "feature_columns": FEATURE_COLUMNS,
        "label_gain": [0, 1, 2, 3],
        "label_column": "relevance",
        "group_columns": ["query_id", "product_locale"],
        "training_rows": len(x_train),
        "validation_rows": len(x_validation),
        "training_query_groups": len(train_group_sizes),
        "validation_query_groups": len(validation_group_sizes),
        "validation_ndcg_at_10": validation_ndcg,
        "best_iteration": int(ranker.best_iteration_ or ranker.n_estimators),
        "random_seed": RANDOM_SEED,
    }

    METADATA_FILE.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print("\nTraining complete.", flush=True)
    print(json.dumps(metadata, indent=2), flush=True)
    print(f"\nModel saved to: {MODEL_FILE}", flush=True)


if __name__ == "__main__":
    main()
