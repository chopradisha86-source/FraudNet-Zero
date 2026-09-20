# XGBoost Risk Model on Real PaySim Data — Before vs After

Sample: 58,213 rows (8213 real fraud cases + 50,000 sampled legitimate transactions)

| Metric | Before (naive) | After (tuned) | Change |
|---|---|---|---|
| Precision | 0.9375 | 0.8759 | -0.0615 |
| Recall | 0.9312 | 0.9933 | +0.0621 |
| F1 | 0.9343 | 0.9309 | -0.0034 |
| PR-AUC | 0.9845 | 0.9893 | +0.0047 |
| ROC-AUC | 0.9970 | 0.9982 | +0.0012 |
| Accuracy (not meaningful under imbalance) | 0.9815 | 0.9792 | -0.0023 |
| Model Size (bytes) | 34,818 | 419,050 | +384,232 |
| Inference Latency (ms/sample) | 0.3384 | 0.3892 | +0.0509 |