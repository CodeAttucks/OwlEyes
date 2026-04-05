import logging
from pathlib import Path
from typing import Any, Dict, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from ..db import get_conn

logger = logging.getLogger(__name__)

# Model storage directory
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)


class BEADMLService:
    """Machine Learning service for BEAD platform predictions."""

    def __init__(self):
        self.coverage_model: RandomForestClassifier | None = None
        self.cost_model: RandomForestRegressor | None = None
        self.scaler = StandardScaler()
        self.load_models()

    def load_models(self):
        """Load pre-trained models from disk."""
        try:
            coverage_path = MODEL_DIR / "coverage_model.pkl"
            if coverage_path.exists():
                self.coverage_model = joblib.load(coverage_path)
                logger.info("Coverage model loaded")

            cost_path = MODEL_DIR / "cost_model.pkl"
            if cost_path.exists():
                self.cost_model = joblib.load(cost_path)
                logger.info("Cost model loaded")
        except Exception as e:
            logger.warning(f"Could not load models: {e}")

    def prepare_training_data(self) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        """Prepare data for model training."""
        try:
            conn = get_conn()

            # Get comprehensive project and location data.
            query = """
                SELECT
                    sl.id,
                    sl.served as target,
                    p.status,
                    COUNT(fr.id) as route_count,
                    COALESCE(SUM(fr.miles), 0) as total_miles,
                    COALESCE(SUM(e.amount), 0) as total_expenditure,
                    COUNT(DISTINCT sl2.id) as nearby_locations,
                    ST_X(sl.geom) as longitude,
                    ST_Y(sl.geom) as latitude
                FROM service_locations sl
                LEFT JOIN projects p ON sl.id = p.id
                LEFT JOIN fiber_routes fr ON p.id = fr.project_id
                LEFT JOIN expenditures e ON p.id = e.project_id
                LEFT JOIN service_locations sl2 ON ST_DWithin(sl.geom, sl2.geom, 5000)
                WHERE sl.served IS NOT NULL
                GROUP BY sl.id, sl.served, p.status, sl.geom
                LIMIT 1000
            """

            df = pd.read_sql(query, conn)
            conn.close()

            if df.empty:
                logger.warning("No training data available")
                return None, None, None, None

            # Prepare features.
            df["status_encoded"] = (df["status"] == "active").astype(int)

            feature_cols = [
                "route_count",
                "total_miles",
                "total_expenditure",
                "nearby_locations",
                "longitude",
                "latitude",
                "status_encoded",
            ]

            X = df[feature_cols].fillna(0)
            y = df["target"].astype(int)

            # Split data.
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

            return X_train, y_train, X_test, y_test
        except Exception as e:
            logger.error(f"Error preparing training data: {e}")
            return None, None, None, None

    def train_coverage_model(self) -> Dict[str, Any]:
        """Train model to predict service coverage."""
        try:
            X_train, y_train, X_test, y_test = self.prepare_training_data()

            if X_train is None:
                return {"status": "error", "message": "Insufficient training data"}

            # Scale features.
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # Train model.
            self.coverage_model = RandomForestClassifier(
                n_estimators=100,
                max_depth=15,
                min_samples_split=5,
                random_state=42,
                n_jobs=-1,
            )
            self.coverage_model.fit(X_train_scaled, y_train)

            # Evaluate.
            train_score = self.coverage_model.score(X_train_scaled, y_train)
            test_score = self.coverage_model.score(X_test_scaled, y_test)

            # Save model.
            joblib.dump(self.coverage_model, MODEL_DIR / "coverage_model.pkl")
            joblib.dump(self.scaler, MODEL_DIR / "scaler.pkl")

            return {
                "status": "success",
                "train_accuracy": round(train_score, 4),
                "test_accuracy": round(test_score, 4),
                "n_samples": len(X_train),
            }
        except Exception as e:
            logger.error(f"Error training coverage model: {e}")
            return {"status": "error", "message": str(e)}

    def predict_coverage(self, features: list) -> Dict[str, Any]:
        """Predict coverage probability for a location."""
        try:
            if self.coverage_model is None:
                return {"error": "Model not trained", "probability": None}

            X = np.array(features).reshape(1, -1)
            X_scaled = self.scaler.transform(X)

            probability = self.coverage_model.predict_proba(X_scaled)[0]
            prediction = self.coverage_model.predict(X_scaled)[0]

            return {
                "prediction": int(prediction),
                "probability_unserved": round(float(probability[0]), 4),
                "probability_served": round(float(probability[1]), 4),
                "confidence": round(float(max(probability)), 4),
            }
        except Exception as e:
            logger.error(f"Error in prediction: {e}")
            return {"error": str(e)}

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from trained model."""
        try:
            if self.coverage_model is None:
                return {}

            feature_names = [
                "route_count",
                "total_miles",
                "total_expenditure",
                "nearby_locations",
                "longitude",
                "latitude",
                "status_encoded",
            ]

            importances = self.coverage_model.feature_importances_
            return dict(zip(feature_names, [round(float(i), 4) for i in importances]))
        except Exception as e:
            logger.error(f"Error getting feature importance: {e}")
            return {}

    def predict_batch(self, features_list: list) -> list:
        """Batch predictions for multiple locations."""
        try:
            if self.coverage_model is None:
                return [{"error": "Model not trained"} for _ in features_list]

            X = np.array(features_list)
            X_scaled = self.scaler.transform(X)
            predictions = self.coverage_model.predict(X_scaled)
            probabilities = self.coverage_model.predict_proba(X_scaled)

            results = []
            for pred, probs in zip(predictions, probabilities):
                results.append(
                    {
                        "prediction": int(pred),
                        "probability_unserved": round(float(probs[0]), 4),
                        "probability_served": round(float(probs[1]), 4),
                        "confidence": round(float(max(probs)), 4),
                    }
                )

            return results
        except Exception as e:
            logger.error(f"Error in batch prediction: {e}")
            return [{"error": str(e)} for _ in features_list]


# Initialize global service
ml_service = BEADMLService()
