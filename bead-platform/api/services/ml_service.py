import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from pathlib import Path
from typing import Dict, Any, Tuple
import logging
from ..db import get_conn

logger = logging.getLogger(__name__)

# Model storage directory
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)

class BEADMLService:
    """Machine Learning service for BEAD platform predictions"""
    
    def __init__(self):
        self.coverage_model: RandomForestClassifier | None = None
        self.cost_model: RandomForestRegressor | None = None
        self.scaler = StandardScaler()
        self.load_models()
    
    def load_models(self):
        """Load pre-trained models from disk"""
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
        """Prepare data for model training"""
        try:
            conn = get_conn()
            
            # Get comprehensive project and location data
            query = \"\"\"\n                SELECT \n                    sl.id,\n                    sl.served as target,\n                    p.status,\n                    COUNT(fr.id) as route_count,\n                    COALESCE(SUM(fr.miles), 0) as total_miles,\n                    COALESCE(SUM(e.amount), 0) as total_expenditure,\n                    COUNT(DISTINCT sl2.id) as nearby_locations,\n                    ST_X(sl.geom) as longitude,\n                    ST_Y(sl.geom) as latitude\n                FROM service_locations sl\n                LEFT JOIN projects p ON sl.id = p.id\n                LEFT JOIN fiber_routes fr ON p.id = fr.project_id\n                LEFT JOIN expenditures e ON p.id = e.project_id\n                LEFT JOIN service_locations sl2 ON ST_DWithin(sl.geom, sl2.geom, 5000)\n                WHERE sl.served IS NOT NULL\n                GROUP BY sl.id, sl.served, p.status, sl.geom\n                LIMIT 1000\n            \"\"\"\n            \n            df = pd.read_sql(query, conn)\n            conn.close()\n            \n            if df.empty:\n                logger.warning(\"No training data available\")\n                return None, None, None, None\n            \n            # Prepare features\n            df['status_encoded'] = (df['status'] == 'active').astype(int)\n            \n            feature_cols = ['route_count', 'total_miles', 'total_expenditure', \n                          'nearby_locations', 'longitude', 'latitude', 'status_encoded']\n            \n            X = df[feature_cols].fillna(0)\n            y = df['target'].astype(int)\n            \n            # Split data\n            X_train, X_test, y_train, y_test = train_test_split(\n                X, y, test_size=0.2, random_state=42\n            )\n            \n            return X_train, y_train, X_test, y_test\n        except Exception as e:\n            logger.error(f\"Error preparing training data: {e}\")\n            return None, None, None, None\n    \n    def train_coverage_model(self) -> Dict[str, Any]:\n        \"\"\"Train model to predict service coverage\"\"\"\n        try:\n            X_train, y_train, X_test, y_test = self.prepare_training_data()\n            \n            if X_train is None:\n                return {\"status\": \"error\", \"message\": \"Insufficient training data\"}\n            \n            # Scale features\n            X_train_scaled = self.scaler.fit_transform(X_train)\n            X_test_scaled = self.scaler.transform(X_test)\n            \n            # Train model\n            self.coverage_model = RandomForestClassifier(\n                n_estimators=100,\n                max_depth=15,\n                min_samples_split=5,\n                random_state=42,\n                n_jobs=-1\n            )\n            self.coverage_model.fit(X_train_scaled, y_train)\n            \n            # Evaluate\n            train_score = self.coverage_model.score(X_train_scaled, y_train)\n            test_score = self.coverage_model.score(X_test_scaled, y_test)\n            \n            # Save model\n            joblib.dump(self.coverage_model, MODEL_DIR / \"coverage_model.pkl\")\n            joblib.dump(self.scaler, MODEL_DIR / \"scaler.pkl\")\n            \n            return {\n                \"status\": \"success\",\n                \"train_accuracy\": round(train_score, 4),\n                \"test_accuracy\": round(test_score, 4),\n                \"n_samples\": len(X_train)\n            }\n        except Exception as e:\n            logger.error(f\"Error training coverage model: {e}\")\n            return {\"status\": \"error\", \"message\": str(e)}\n    \n    def predict_coverage(self, features: list) -> Dict[str, Any]:\n        \"\"\"Predict coverage probability for a location\"\"\"\n        try:\n            if self.coverage_model is None:\n                return {\"error\": \"Model not trained\", \"probability\": None}\n            \n            X = np.array(features).reshape(1, -1)\n            X_scaled = self.scaler.transform(X)\n            \n            probability = self.coverage_model.predict_proba(X_scaled)[0]\n            prediction = self.coverage_model.predict(X_scaled)[0]\n            \n            return {\n                \"prediction\": int(prediction),\n                \"probability_unserved\": round(float(probability[0]), 4),\n                \"probability_served\": round(float(probability[1]), 4),\n                \"confidence\": round(float(max(probability)), 4)\n            }\n        except Exception as e:\n            logger.error(f\"Error in prediction: {e}\")\n            return {\"error\": str(e)}\n    \n    def get_feature_importance(self) -> Dict[str, float]:\n        \"\"\"Get feature importance from trained model\"\"\"\n        try:\n            if self.coverage_model is None:\n                return {}\n            \n            feature_names = ['route_count', 'total_miles', 'total_expenditure',\n                          'nearby_locations', 'longitude', 'latitude', 'status_encoded']\n            \n            importances = self.coverage_model.feature_importances_\n            return dict(zip(feature_names, [round(float(i), 4) for i in importances]))\n        except Exception as e:\n            logger.error(f\"Error getting feature importance: {e}\")\n            return {}\n    \n    def predict_batch(self, features_list: list) -> list:\n        \"\"\"Batch predictions for multiple locations\"\"\"\n        try:\n            if self.coverage_model is None:\n                return [{\"error\": \"Model not trained\"} for _ in features_list]\n            \n            X = np.array(features_list)\n            X_scaled = self.scaler.transform(X)\n            predictions = self.coverage_model.predict(X_scaled)\n            probabilities = self.coverage_model.predict_proba(X_scaled)\n            \n            results = []\n            for i, (pred, probs) in enumerate(zip(predictions, probabilities)):\n                results.append({\n                    \"prediction\": int(pred),\n                    \"probability_unserved\": round(float(probs[0]), 4),\n                    \"probability_served\": round(float(probs[1]), 4),\n                    \"confidence\": round(float(max(probs)), 4)\n                })\n            \n            return results\n        except Exception as e:\n            logger.error(f\"Error in batch prediction: {e}\")\n            return [{\"error\": str(e)} for _ in features_list]\n\n# Initialize global service\nml_service = BEADMLService()