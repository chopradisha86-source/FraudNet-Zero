
import time
import numpy as np
from gqlalchemy import Memgraph
import xgboost as xgb
import shap

memgraph = Memgraph(host="127.0.0.1", port=7687)


class RealTimeRiskAgent:
    def __init__(self, model_path: str = None):
        self.feature_names = [
            "Graph Ring Topology",
            "Transaction Velocity Spike",
            "Device/IP Fingerprint Jump",
            "Burst Ratio Anomaly",
            "Account Dormancy Reactivation",
        ]
        self.model = self._load_or_create_model(model_path)
        self.explainer = shap.TreeExplainer(self.model)

    def _load_or_create_model(self, model_path: str):
        """
        Loads a pre-trained XGBoost model, or initializes one with TUNED
        hyperparameters (found via grid search + early stopping in
        benchmarks/train_and_benchmark_real_data.py) on synthetic baseline
        data for inference-schema initialization.

        CHANGED from original: max_depth 4->6, eta 0.1->0.05, added
        reg_lambda=2.0 (L2 regularization), num_boost_round now selected
        via early stopping (up to 200) instead of a fixed 20.
        """
        model = xgb.Booster()
        if model_path:
            try:
                model.load_model(model_path)
                print(f"\u2705 Pre-trained XGBoost model loaded from {model_path}.")
                return model
            except Exception as e:
                print(f"\u26a0\ufe0f Failed to load model from path ({e}). Falling back to baseline init...")

        X_dummy = np.random.rand(500, 5)
        y_dummy = (X_dummy[:, 0] * 0.45 + X_dummy[:, 1] * 0.35 + X_dummy[:, 2] * 0.20 > 0.5).astype(int)

        X_train, X_val = X_dummy[:400], X_dummy[400:]
        y_train, y_val = y_dummy[:400], y_dummy[400:]

        dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=self.feature_names)
        dval = xgb.DMatrix(X_val, label=y_val, feature_names=self.feature_names)

        params = {
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "max_depth": 6,       # was 4
            "eta": 0.05,          # was 0.1
            "reg_lambda": 2.0,    # was unset (no regularization)
        }
        model = xgb.train(
            params, dtrain,
            num_boost_round=200,               # was fixed 20
            evals=[(dval, "validation")],
            early_stopping_rounds=15,          # was not used
            verbose_eval=False,
        )
        return model

    def retrain_on_labeled_data(self, X: np.ndarray, y: np.ndarray, save_path: str = None):
        """
        NEW METHOD -- not in the original file.

        Retrains the model on real labeled data using the same tuned
        hyperparameters, with proper train/val split and early stopping.
        Call this with your actual production feature data (extracted via
        the same 5-feature schema this class uses) once you have enough
        labeled Memgraph history to train on. This is what actually closes
        the "production model isn't tuned" gap -- the constructor alone
        only changes the SYNTHETIC baseline's hyperparameters.
        """
        from sklearn.model_selection import train_test_split

        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42,
            stratify=y if len(set(y)) > 1 else None
        )
        dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=self.feature_names)
        dval = xgb.DMatrix(X_val, label=y_val, feature_names=self.feature_names)

        pos = (y_train == 1).sum()
        neg = (y_train == 0).sum()
        scale_pos_weight = (neg / pos) if pos > 0 else 1.0

        params = {
            "objective": "binary:logistic",
            "eval_metric": "aucpr",
            "max_depth": 6,
            "eta": 0.05,
            "reg_lambda": 2.0,
            "scale_pos_weight": scale_pos_weight,
        }
        self.model = xgb.train(
            params, dtrain,
            num_boost_round=300,
            evals=[(dval, "validation")],
            early_stopping_rounds=20,
            verbose_eval=False,
        )
        self.explainer = shap.TreeExplainer(self.model)

        if save_path:
            self.model.save_model(save_path)
            print(f"\U0001F4BE Retrained model saved to {save_path}")

        print(f"\u2705 Retrained on {len(X)} labeled examples (scale_pos_weight={scale_pos_weight:.1f})")

    # --- everything below this line is UNCHANGED from your original risk_agent.py ---

    def calculate_shap_attributions(self, feature_vector: list) -> list:
        dmatrix = xgb.DMatrix([feature_vector], feature_names=self.feature_names)
        shap_values = self.explainer.shap_values(dmatrix)[0]
        abs_shap = np.abs(shap_values)
        total_shap = np.sum(abs_shap) if np.sum(abs_shap) > 0 else 1.0
        features = []
        for idx, name in enumerate(self.feature_names):
            score = float(shap_values[idx])
            percentage = float((abs(score) / total_shap) * 100)
            features.append({"feature": name, "impact_score": round(score, 4), "percentage": f"{round(percentage, 1)}%"})
        return sorted(features, key=lambda x: abs(x["impact_score"]), reverse=True)[:5]

    def predict_risk_score(self, feature_vector: list) -> float:
        dmatrix = xgb.DMatrix([feature_vector], feature_names=self.feature_names)
        probability = float(self.model.predict(dmatrix)[0])
        return round(probability * 100, 2)

    def analyze_and_score_accounts(self) -> list:
        query = """
        MATCH (a:Account)-[r:TRANSFERRED]->(b:Account)
        WITH a, count(r) AS tx_count, collect(r.ip) AS ips, collect(r.device) AS devices
        OPTIONAL MATCH ring_path = (a)-[:TRANSFERRED*3..6]->(a)
        WITH a, tx_count, ips, devices, (ring_path IS NOT NULL) AS in_ring,
             (size(ips) > 1 OR size(devices) > 1) AS multi_device_ip
        RETURN a.id AS account_id, tx_count, in_ring, multi_device_ip
        """
        try:
            raw_results = list(memgraph.execute_and_fetch(query))
            processed_scores = []
            for row in raw_results:
                account_id = row["account_id"]
                tx_count = row["tx_count"]
                in_ring = 1.0 if row["in_ring"] else 0.0
                multi_device = 1.0 if row["multi_device_ip"] else 0.0
                feature_vector = [in_ring, min(1.0, tx_count / 10.0), multi_device, 0.08, 0.04]
                risk_score = self.predict_risk_score(feature_vector)
                shap_attributions = self.calculate_shap_attributions(feature_vector)
                if risk_score >= 75.0:
                    risk_level = "CRITICAL"
                elif risk_score >= 50.0:
                    risk_level = "HIGH"
                elif risk_score >= 25.0:
                    risk_level = "MEDIUM"
                else:
                    risk_level = "LOW"
                update_query = "MATCH (a:Account {id: $id}) SET a.risk_score = $score, a.risk_level = $level"
                memgraph.execute(update_query, {"id": account_id, "score": risk_score, "level": risk_level})
                processed_scores.append({
                    "account_id": account_id, "risk_score": risk_score,
                    "risk_level": risk_level, "shap_attributions": shap_attributions,
                })
            processed_scores.sort(key=lambda x: x["risk_score"], reverse=True)
            return processed_scores[:10]
        except Exception as e:
            print(f"\u274c Error computing ML risk scores: {e}")
            return []