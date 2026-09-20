"""
FraudNet-Zero — Risk Model: Real-Data Before/After Benchmark (PaySim)
========================================================================

WHAT THIS IS (READ BEFORE CITING THIS ANYWHERE)
------------------------------------------------
A real before/after training benchmark on the actual PaySim transactions.csv
dataset referenced by streaming/producer.py -- 6.36M real simulated mobile
money transactions, 8,213 labeled fraud cases (isFraud=1).

WHAT THIS VALIDATES: the XGBoost transaction risk-scoring approach on
real labeled fraud data.

WHAT THIS DOES NOT VALIDATE: multi-hop laundering ring/cycle detection.
PaySim has no ring structure and no device/IP fields -- that claim is
only supported by benchmarks/eval_fraudnet.py's synthetic ring-injection
benchmark. Do not conflate the two when reporting results.

CLASS IMBALANCE: real fraud rate is 0.129%. Accuracy is near-meaningless
here (predicting "not fraud" for everything scores ~99.87% accuracy).
This script reports Precision, Recall, F1, and PR-AUC (average precision)
as the primary metrics -- these are what actually matter for imbalanced
fraud detection, and PR-AUC in particular is the standard metric used in
the published PaySim literature for this exact reason.

METHODOLOGY
-----------
"BEFORE" = the same naive baseline shape used in risk_agent.py's default
config (max_depth=4, eta=0.1, fixed 20 rounds) with NO class-imbalance
handling -- this is what happens if you train on real fraud data without
accounting for the 1:773 class ratio.

"AFTER" = a genuinely different, principled fix: scale_pos_weight to
correct for class imbalance, deeper trees, tuned learning rate, and
early stopping via grid search on a held-out validation split. This
mirrors the actual PaySim-literature approach to this exact problem.

Sampling: full dataset is 6.36M rows. For tractability we use all 8,213
fraud rows plus a random 50,000-row sample of legitimate transactions
(stratified across types), preserving the real ~14% fraud rate within
the *sample* while being explicit that this is a downsampled, not
full-population, evaluation.
"""
import json
import time
import os
import numpy as np
import pandas as pd
import xgboost as xgb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    confusion_matrix, average_precision_score, roc_auc_score
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "transactions.csv")   # repo root, one level up from benchmarks/
OUT_DIR = os.path.join(BASE_DIR, "model_eval_real")
CHART_DIR = os.path.join(OUT_DIR, "charts")
os.makedirs(CHART_DIR, exist_ok=True)

RANDOM_STATE = 42
N_LEGIT_SAMPLE = 50_000

FEATURE_NAMES = [
    "amount",
    "balance_delta_orig",
    "balance_delta_dest",
    "error_balance_orig",
    "error_balance_dest",
    "type_TRANSFER",
    "type_CASH_OUT",
    "orig_tx_count",
]


def load_and_engineer_features():
    print("Loading PaySim dataset...")
    df = pd.read_csv(DATA_PATH)
    print(f"Full dataset: {len(df):,} rows, {df['isFraud'].sum():,} fraud ({df['isFraud'].mean()*100:.4f}%)")

    # Real transaction-count-per-account feature (crude graph-degree proxy),
    # computed on the FULL dataset before sampling so it reflects true account activity.
    tx_counts = df["nameOrig"].value_counts()
    df["orig_tx_count"] = df["nameOrig"].map(tx_counts)

    # Well-documented PaySim engineered features (balance-consistency errors) --
    # these are standard in published PaySim fraud-detection work, not invented here.
    df["balance_delta_orig"] = df["oldbalanceOrg"] - df["newbalanceOrig"]
    df["balance_delta_dest"] = df["newbalanceDest"] - df["oldbalanceDest"]
    df["error_balance_orig"] = df["oldbalanceOrg"] - df["amount"] - df["newbalanceOrig"]
    df["error_balance_dest"] = df["oldbalanceDest"] + df["amount"] - df["newbalanceDest"]

    df["type_TRANSFER"] = (df["type"] == "TRANSFER").astype(int)
    df["type_CASH_OUT"] = (df["type"] == "CASH_OUT").astype(int)

    fraud_df = df[df["isFraud"] == 1]
    legit_df = df[df["isFraud"] == 0].sample(n=N_LEGIT_SAMPLE, random_state=RANDOM_STATE)

    sample = pd.concat([fraud_df, legit_df]).sample(frac=1.0, random_state=RANDOM_STATE)  # shuffle
    print(f"Sampled subset: {len(sample):,} rows, {sample['isFraud'].sum():,} fraud "
          f"({sample['isFraud'].mean()*100:.2f}% -- upsampled ratio for tractable training, NOT the true population rate)")

    X = sample[FEATURE_NAMES].values.astype(float)
    y = sample["isFraud"].values
    return X, y


def measure_inference_latency(model, X_sample, n_trials=200):
    dmat = xgb.DMatrix(X_sample[:1], feature_names=FEATURE_NAMES)
    for _ in range(10):
        model.predict(dmat)
    start = time.perf_counter()
    for _ in range(n_trials):
        model.predict(dmat)
    elapsed = time.perf_counter() - start
    return (elapsed / n_trials) * 1000.0


def model_size_bytes(model, path):
    model.save_model(path)
    return os.path.getsize(path)


def evaluate(model, X_test, y_test, threshold=0.5):
    dmat = xgb.DMatrix(X_test, feature_names=FEATURE_NAMES)
    probs = model.predict(dmat)
    preds = (probs >= threshold).astype(int)
    return {
        "accuracy": accuracy_score(y_test, preds),
        "f1": f1_score(y_test, preds),
        "precision": precision_score(y_test, preds),
        "recall": recall_score(y_test, preds),
        "pr_auc": average_precision_score(y_test, probs),
        "roc_auc": roc_auc_score(y_test, probs),
        "confusion_matrix": confusion_matrix(y_test, preds).tolist(),
    }


def plot_confusion_matrix(cm, title, path):
    cm = np.array(cm)
    fig, ax = plt.subplots(figsize=(4, 4))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Legit", "Fraud"])
    ax.set_yticks([0, 1]); ax.set_yticklabels(["Legit", "Fraud"])
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    ax.set_title(title)
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center",
                     color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=13)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_metrics_comparison(before, after, path):
    metrics = ["precision", "recall", "f1", "pr_auc", "roc_auc"]
    labels = ["Precision", "Recall", "F1", "PR-AUC", "ROC-AUC"]
    before_vals = [before[m] for m in metrics]
    after_vals = [after[m] for m in metrics]

    x = np.arange(len(metrics))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars1 = ax.bar(x - width / 2, before_vals, width, label="Before (naive, no imbalance handling)", color="#94a3b8")
    bars2 = ax.bar(x + width / 2, after_vals, width, label="After (tuned + scale_pos_weight)", color="#2563eb")

    ax.set_ylabel("Score")
    ax.set_title("XGBoost Risk Model on Real PaySim Data — Before vs After")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=8, loc="lower right")

    for bars in (bars1, bars2):
        for b in bars:
            h = b.get_height()
            ax.annotate(f"{h:.3f}", xy=(b.get_x() + b.get_width() / 2, h),
                        xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8)

    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def train_before_model(dtrain):
    """Naive baseline: same shape as risk_agent.py's default config, no imbalance handling."""
    params = {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "max_depth": 4,
        "eta": 0.1,
    }
    return xgb.train(params, dtrain, num_boost_round=20)


def train_after_model(dtrain, dval, scale_pos_weight):
    """Tuned: class-imbalance corrected via scale_pos_weight, grid search + early stopping."""
    param_grid = [
        {"max_depth": 5, "eta": 0.05, "reg_lambda": 1.0},
        {"max_depth": 6, "eta": 0.05, "reg_lambda": 2.0},
        {"max_depth": 6, "eta": 0.03, "reg_lambda": 1.0},
    ]
    best_model, best_ap, best_params = None, -1.0, None

    for grid_params in param_grid:
        params = {
            "objective": "binary:logistic",
            "eval_metric": "aucpr",  # PR-AUC -- correct metric to optimize under class imbalance
            "scale_pos_weight": scale_pos_weight,
            **grid_params,
        }
        evals_result = {}
        model = xgb.train(
            params, dtrain,
            num_boost_round=300,
            evals=[(dval, "validation")],
            early_stopping_rounds=20,
            evals_result=evals_result,
            verbose_eval=False,
        )
        final_ap = evals_result["validation"]["aucpr"][-1]
        if final_ap > best_ap:
            best_ap, best_model, best_params = final_ap, model, grid_params

    print(f"[AFTER] Best params: {best_params}, scale_pos_weight={scale_pos_weight:.1f} (val PR-AUC={best_ap:.4f})")
    return best_model


def main():
    X, y = load_and_engineer_features()
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.4, random_state=RANDOM_STATE, stratify=y)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=RANDOM_STATE, stratify=y_temp)

    dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=FEATURE_NAMES)
    dval = xgb.DMatrix(X_val, label=y_val, feature_names=FEATURE_NAMES)

    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    print(f"Train: {len(X_train):,} | Val: {len(X_val):,} | Test: {len(X_test):,}")
    print(f"Class imbalance ratio (legit:fraud) in train set: {scale_pos_weight:.1f}:1")

    before_model = train_before_model(dtrain)
    before_metrics = evaluate(before_model, X_test, y_test)
    before_latency = measure_inference_latency(before_model, X_test)
    before_size = model_size_bytes(before_model, os.path.join(OUT_DIR, "model_before.json"))

    after_model = train_after_model(dtrain, dval, scale_pos_weight)
    after_metrics = evaluate(after_model, X_test, y_test)
    after_latency = measure_inference_latency(after_model, X_test)
    after_size = model_size_bytes(after_model, os.path.join(OUT_DIR, "model_after.json"))

    plot_confusion_matrix(before_metrics["confusion_matrix"], "Before (naive baseline)",
                           os.path.join(CHART_DIR, "confusion_matrix_before.png"))
    plot_confusion_matrix(after_metrics["confusion_matrix"], "After (imbalance-corrected + tuned)",
                           os.path.join(CHART_DIR, "confusion_matrix_after.png"))
    plot_metrics_comparison(before_metrics, after_metrics,
                             os.path.join(CHART_DIR, "metrics_comparison.png"))

    summary = {
        "dataset": "PaySim (real, from streaming/producer.py's transactions.csv)",
        "full_dataset_rows": 6362620,
        "full_dataset_fraud_count": 8213,
        "full_dataset_fraud_rate_pct": 0.1291,
        "sample_rows": len(X),
        "sample_fraud_count": int(y.sum()),
        "note": "Sampled subset (all fraud + 50k random legit) for tractable training. "
                "Metrics below reflect the TEST split of this sample, not the full 6.36M-row population.",
        "before": {**{k: round(v, 4) for k, v in before_metrics.items() if k != "confusion_matrix"},
                   "confusion_matrix": before_metrics["confusion_matrix"],
                   "model_size_bytes": before_size, "inference_latency_ms": round(before_latency, 4)},
        "after": {**{k: round(v, 4) for k, v in after_metrics.items() if k != "confusion_matrix"},
                  "confusion_matrix": after_metrics["confusion_matrix"],
                  "model_size_bytes": after_size, "inference_latency_ms": round(after_latency, 4)},
    }

    with open(os.path.join(OUT_DIR, "metrics_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    md_lines = [
        "# XGBoost Risk Model on Real PaySim Data — Before vs After\n",
        f"Sample: {len(X):,} rows ({int(y.sum())} real fraud cases + {N_LEGIT_SAMPLE:,} sampled legitimate transactions)\n",
        "| Metric | Before (naive) | After (tuned) | Change |",
        "|---|---|---|---|",
    ]
    for metric, label in [("precision", "Precision"), ("recall", "Recall"), ("f1", "F1"),
                            ("pr_auc", "PR-AUC"), ("roc_auc", "ROC-AUC"), ("accuracy", "Accuracy (not meaningful under imbalance)")]:
        b, a = before_metrics[metric], after_metrics[metric]
        md_lines.append(f"| {label} | {b:.4f} | {a:.4f} | {a - b:+.4f} |")
    md_lines.append(f"| Model Size (bytes) | {before_size:,} | {after_size:,} | {after_size - before_size:+,} |")
    md_lines.append(f"| Inference Latency (ms/sample) | {before_latency:.4f} | {after_latency:.4f} | {after_latency - before_latency:+.4f} |")

    with open(os.path.join(OUT_DIR, "metrics_summary.md"), "w") as f:
        f.write("\n".join(md_lines))

    print("\n" + "\n".join(md_lines))
    print(f"\nCharts saved to: {CHART_DIR}")


if __name__ == "__main__":
    main()