from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel
from typing import List, Optional
import pickle
import os
import numpy as np
import sqlite3

def get_db_connection():
    """Obtener conexión a la base de datos"""
    # Obtener la ruta a la base de datos
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(os.path.dirname(current_dir))
    db_path = os.path.join(backend_dir, 'marvel_cards.db')
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Para obtener resultados como diccionarios
    return conn

router = APIRouter()

# Path al modelo entrenado
MODEL_PATH = os.path.join(
    os.path.dirname(__file__), 
    '..', 'saved_models', 'villain_svm_model.pkl'
)

# Cache del modelo cargado
_model = None

def load_model():
    """
    Carga el modelo entrenado (con cache)
    """
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            return None
        with open(MODEL_PATH, 'rb') as f:
            _model = pickle.load(f)
    return _model

# Esquemas de datos
class DeckData(BaseModel):
    hero_id: int
    aspect: str  # 'aggression', 'justice', 'leadership', 'protection'
    cards: List[dict]  # Lista de cartas (por ahora no se usa, pero está para futuro)
    villain_id: Optional[int] = None  # Si se proporciona, predice solo para ese villano
    difficulty: Optional[str] = 'normal'  # 'normal' o 'expert'

class PredictionResponse(BaseModel):
    villain_id: int
    villain_name: str
    win_probability: float  # 0.0 a 1.0 (0% a 100%)
    recommendation: str  # 'recommended', 'neutral', 'not_recommended'
    confidence: str  # 'high', 'medium', 'low'
    reason: str

@router.post("/recommendations/train", status_code=200)
async def train_model_endpoint(
    x_auth0_id: Optional[str] = Header(None, alias="X-Auth0-ID")
):
    """
    Endpoint para entrenar el modelo (útil para reentrenar periódicamente)
    """
    try:
        from ml.models.train_model import train_villain_recommender
        
        model = train_villain_recommender()
        
        if model:
            return {
                "message": "Modelo entrenado exitosamente",
                "status": "success",
                "model_path": MODEL_PATH
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Error al entrenar el modelo. Verifica que haya suficientes datos de partidas (mínimo 10)."
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al entrenar el modelo: {str(e)}"
        )

@router.post("/recommendations/villain", response_model=dict, status_code=200)
async def predict_villain_success(
    deck_data: DeckData,
    x_auth0_id: Optional[str] = Header(None, alias="X-Auth0-ID")
):
    """
    Predice la probabilidad de victoria de un mazo contra villanos
    
    Si se proporciona villain_id, predice solo para ese villano.
    Si no, predice para todos los villanos y devuelve recomendaciones ordenadas.
    
    Request Body:
    {
        "hero_id": 1,
        "aspect": "aggression",
        "cards": [...],
        "villain_id": 994808,  // Opcional
        "difficulty": "normal"  // Opcional, default: "normal"
    }
    
    Response:
    {
        "recommendations": [
            {
                "villain_id": 994808,
                "villain_name": "Rhino",
                "win_probability": 0.75,
                "recommendation": "recommended",
                "confidence": "medium",
                "reason": "Mazos similares tienen 75% de probabilidad de victoria"
            },
            ...
        ]
    }
    """
    model = load_model()
    
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Modelo de IA no disponible. Necesita ser entrenado primero. Ejecuta: python -m ml.models.train_model"
        )
    
    # Validar aspect
    valid_aspects = ['aggression', 'justice', 'leadership', 'protection']
    if deck_data.aspect not in valid_aspects:
        raise HTTPException(
            status_code=400,
            detail=f"Aspecto inválido. Debe ser uno de: {valid_aspects}"
        )
    
    # Validar difficulty
    if deck_data.difficulty not in ['normal', 'expert']:
        raise HTTPException(
            status_code=400,
            detail="Dificultad inválida. Debe ser 'normal' o 'expert'"
        )
    
    # Codificar aspect
    aspect_map = {
        'aggression': 0,
        'justice': 1,
        'leadership': 2,
        'protection': 3
    }
    aspect_encoded = aspect_map[deck_data.aspect]
    
    # Codificar difficulty
    difficulty_encoded = 0 if deck_data.difficulty == 'normal' else 1
    
    # Si se proporciona un villano específico
    if deck_data.villain_id:
        villain_name = get_villain_name(deck_data.villain_id)
        if not villain_name:
            raise HTTPException(
                status_code=404,
                detail=f"Villano con ID {deck_data.villain_id} no encontrado"
            )
        
        # Preparar features: [hero_id, aspect_encoded, villain_id, difficulty_encoded]
        features = np.array([[
            deck_data.hero_id,
            aspect_encoded,
            deck_data.villain_id,
            difficulty_encoded
        ]])
        
        # Predecir probabilidad
        win_prob = model.predict_proba(features)[0][1]  # Probabilidad de ganar (clase 1)
        
        # Determinar recomendación
        if win_prob >= 0.65:
            recommendation = 'recommended'
        elif win_prob >= 0.45:
            recommendation = 'neutral'
        else:
            recommendation = 'not_recommended'
        
        # Calcular confianza (basado en cantidad de datos de entrenamiento)
        # TODO: Mejorar cálculo de confianza
        confidence = 'medium'
        
        return {
            "recommendations": [PredictionResponse(
                villain_id=deck_data.villain_id,
                villain_name=villain_name,
                win_probability=float(win_prob),
                recommendation=recommendation,
                confidence=confidence,
                reason=f"Mazos similares tienen {win_prob*100:.0f}% de probabilidad de victoria contra {villain_name}"
            ).dict()]
        }
    
    # Si no se proporciona villano, predecir para todos
    else:
        villains = get_all_villains()
        
        if not villains:
            raise HTTPException(
                status_code=500,
                detail="No se pudieron obtener los villanos de la base de datos"
            )
        
        predictions = []
        for villain in villains:
            features = np.array([[
                deck_data.hero_id,
                aspect_encoded,
                villain['id'],
                difficulty_encoded
            ]])
            
            win_prob = model.predict_proba(features)[0][1]
            
            # Determinar recomendación
            if win_prob >= 0.65:
                recommendation = 'recommended'
            elif win_prob >= 0.45:
                recommendation = 'neutral'
            else:
                recommendation = 'not_recommended'
            
            # Calcular confianza
            confidence = 'medium'  # TODO: Mejorar cálculo
            
            predictions.append(PredictionResponse(
                villain_id=villain['id'],
                villain_name=villain['name'],
                win_probability=float(win_prob),
                recommendation=recommendation,
                confidence=confidence,
                reason=f"Mazos similares tienen {win_prob*100:.0f}% de probabilidad de victoria"
            ).dict())
        
        # Ordenar por probabilidad de victoria (mayor a menor)
        predictions.sort(key=lambda x: x['win_probability'], reverse=True)
        
        return {"recommendations": predictions}

def get_villain_name(villain_id: int) -> Optional[str]:
    """
    Obtiene el nombre de un villano por su ID (card_set)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT card_set 
            FROM cards 
            WHERE id = ? AND type = 'villain'
        ''', (villain_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result["card_set"] if result and result["card_set"] else None
    except Exception as e:
        print(f"Error obteniendo villano: {e}")
        return None

def get_all_villains() -> List[dict]:
    """
    Obtiene todos los villanos únicos de la base de datos
    Usa el mismo método que get_villains_with_ids en main.py
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT MIN(id) as id, card_set as name
            FROM cards 
            WHERE type = 'villain' AND card_set IS NOT NULL
            GROUP BY card_set
            ORDER BY card_set
        ''')
        results = cursor.fetchall()
        conn.close()
        
        return [{"id": row["id"], "name": row["name"]} for row in results]
    except Exception as e:
        print(f"Error obteniendo villanos: {e}")
        return []

