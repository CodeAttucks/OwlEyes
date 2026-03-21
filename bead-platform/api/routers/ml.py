from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from services.ml_service import ml_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml")

class PredictionRequest(BaseModel):
    features: List[float]

class BatchPredictionRequest(BaseModel):
    features_list: List[List[float]]

@router.post("/train")
def train_model():
    """Train the coverage prediction model"""
    try:
        result = ml_service.train_coverage_model()
        return result
    except Exception as e:
        logger.error(f"Training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/predict")
def predict(request: PredictionRequest):
    """Predict coverage for a single location"""
    try:
        if len(request.features) != 7:
            raise ValueError("Expected 7 features: route_count, total_miles, total_expenditure, nearby_locations, longitude, latitude, status_encoded")
        
        result = ml_service.predict_coverage(request.features)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/predict/batch")
def predict_batch(request: BatchPredictionRequest):
    """Batch predictions for multiple locations"""
    try:
        if not request.features_list:
            raise ValueError("features_list cannot be empty")
        
        # Validate feature count
        if any(len(features) != 7 for features in request.features_list):
            raise ValueError("Each feature set must have exactly 7 features")
        
        results = ml_service.predict_batch(request.features_list)
        return {"predictions": results, "count": len(results)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/features/importance")
def get_feature_importance():
    """Get feature importance from the trained model"""
    try:
        importance = ml_service.get_feature_importance()
        
        if not importance:
            raise HTTPException(status_code=400, detail="Model not trained yet")
        
        return {
            "features": importance,
            "total_importance": sum(importance.values())
        }
    except Exception as e:
        logger.error(f"Error getting feature importance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/model/status")
def get_model_status():
    """Get status of ML models"""
    try:
        return {
            "coverage_model_trained": ml_service.coverage_model is not None,
            "cost_model_trained": ml_service.cost_model is not None,
            "scaler_ready": ml_service.scaler is not None
        }
    except Exception as e:
        logger.error(f"Error getting model status: {e}")
        raise HTTPException(status_code=500, detail=str(e))