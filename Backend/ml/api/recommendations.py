from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel
from typing import List, Optional
import pickle
import os
import numpy as np
import sqlite3
import json
import random

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

class DeckGenerationRequest(BaseModel):
    villain_id: int
    difficulty: str  # 'normal' o 'expert'
    patches: Optional[List[str]] = []  # Por ahora vacío, se implementará después

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

def get_best_hero_aspect_for_villain(villain_id: int, difficulty: str) -> Optional[dict]:
    """
    El SVM (IA) decide la mejor combinación héroe/aspecto contra el villano.
    
    CÓMO FUNCIONA:
    1. El SVM se entrena con TODAS las partidas históricas (203 partidas)
    2. El SVM aprende patrones: qué héroes/aspectos funcionan bien en general
    3. Para este villano, solo consideramos combinaciones que tienen al menos 1 partida histórica
    4. El SVM predice la probabilidad de victoria para cada combinación
    5. El SVM decide 100% - el win rate histórico solo se muestra como información
    
    Returns: {'hero_id': int, 'aspect': str, 'win_probability': float, 'win_rate': float} o None
    """
    model = load_model()
    if not model:
        return None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener combinaciones que tienen al menos 1 partida contra este villano
        # Esto es solo para saber QUÉ combinaciones considerar, NO para decidir
        cursor.execute('''
            SELECT 
                d.hero_id, 
                d.aspect,
                COUNT(*) as total_games,
                SUM(CASE WHEN gc.result = 'win' THEN 1 ELSE 0 END) as wins,
                CAST(SUM(CASE WHEN gc.result = 'win' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as win_rate
            FROM game_configurations gc
            JOIN decks d ON gc.deck_id = d.id
            WHERE gc.villain_id = ?
                AND gc.difficulty = ?
                AND d.hero_id IS NOT NULL
                AND d.aspect IS NOT NULL
            GROUP BY d.hero_id, d.aspect
            HAVING COUNT(*) > 0
        ''', (villain_id, difficulty))
        
        historical_combinations = cursor.fetchall()
        conn.close()
        
        if not historical_combinations:
            print(f"⚠️  No hay datos históricos contra este villano en dificultad {difficulty}. No se puede recomendar nada.")
            return None
        
        # FILTRO: Solo considerar combinaciones que han GANADO al menos una vez
        # Queremos recomendar mazos que GANEN, no que pierdan
        winning_combinations = [row for row in historical_combinations if row['win_rate'] > 0]
        
        if not winning_combinations:
            # Si todas han perdido, no podemos recomendar nada (no hay mazos ganadores)
            print(f"⚠️  Todas las combinaciones han perdido contra este villano. No se puede recomendar ningún mazo ganador.")
            return None
        
        # EL SVM DECIDE 100% ENTRE LAS COMBINACIONES GANADORAS
        # El SVM elige la mejor entre las que sabemos que pueden ganar
        aspect_map = {'aggression': 0, 'justice': 1, 'leadership': 2, 'protection': 3}
        difficulty_encoded = 0 if difficulty == 'normal' else 1
        
        best_combination = None
        best_svm_prob = -1.0
        
        print(f"🤖 SVM (IA) analizando {len(winning_combinations)} combinaciones GANADORAS contra este villano...")
        print(f"   El SVM usa su conocimiento aprendido de TODAS las partidas para elegir la mejor")
        
        for row in winning_combinations:
            hero_id = row["hero_id"]
            aspect = row["aspect"]
            win_rate = row["win_rate"]
            total_games = row["total_games"]
            
            # Preparar features para el SVM: [hero_id, aspect, villain_id, difficulty]
            features = np.array([[
                hero_id,
                aspect_map[aspect],
                villain_id,
                difficulty_encoded
            ]])
            
            # EL SVM PREDICE - ESTO ES LO ÚNICO QUE IMPORTA
            svm_prob = model.predict_proba(features)[0][1]
            
            # El SVM decide 100% - solo comparamos sus predicciones
            if svm_prob > best_svm_prob:
                best_svm_prob = svm_prob
                best_combination = {
                    "hero_id": hero_id,
                    "aspect": aspect,
                    "win_probability": float(svm_prob),  # Predicción del SVM (la IA decide)
                    "win_rate": float(win_rate),  # Solo información para mostrar
                    "total_games": int(total_games),
                    "wins": int(row["wins"])
                }
        
        if best_combination:
            hero_name = get_hero_name(best_combination['hero_id'])
            print(f"✅ SVM (IA) recomienda: {hero_name} + {best_combination['aspect']}")
            print(f"   Predicción SVM (IA): {best_combination['win_probability']:.2%} ← EL SVM DECIDE")
            print(f"   Win rate histórico (solo info): {best_combination['win_rate']:.2%} ({best_combination['wins']}/{best_combination['total_games']})")
        
        return best_combination
    except Exception as e:
        print(f"Error obteniendo mejor héroe/aspecto con SVM: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_all_heroes() -> List[dict]:
    """Obtiene todos los héroes disponibles"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT id, name
            FROM cards 
            WHERE type = 'hero'
            ORDER BY name
        ''')
        results = cursor.fetchall()
        conn.close()
        
        return [{"id": row["id"], "name": row["name"]} for row in results]
    except Exception as e:
        print(f"Error obteniendo héroes: {e}")
        return []

def get_hero_specific_cards(hero_id: int) -> List[dict]:
    """Obtiene las cartas específicas del héroe (15-16 cartas)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar el héroe por ID para obtener su card_set y pack_name
        cursor.execute('''
            SELECT card_set, pack_name FROM cards 
            WHERE id = ? AND type = 'hero'
        ''', (hero_id,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return []
        
        hero_card_set = result["card_set"]
        hero_pack_name = result["pack_name"]
        
        # Buscar las cartas que pertenecen al héroe
        cursor.execute('''
            SELECT id, name, cost, type, aspect, card_set, quantity, deck_limit
            FROM cards 
            WHERE card_set = ? 
            AND pack_name = ?
            AND type != 'hero' 
            AND LOWER(type) != 'alter_ego' 
            AND LOWER(type) != 'alter-ego'
            AND aspect = 'hero'
            ORDER BY type, cost, name
        ''', (hero_card_set, hero_pack_name))
        
        hero_cards = []
        for row in cursor.fetchall():
            quantity = row["quantity"] or 1
            hero_cards.append({
                "card_id": row["id"],
                "card_name": row["name"],
                "card_set": row["card_set"] or hero_pack_name or "Unknown",
                "quantity": quantity
            })
        
        conn.close()
        return hero_cards
    except Exception as e:
        print(f"Error obteniendo cartas del héroe: {e}")
        return []

def get_aspect_cards_for_deck(aspect: str, needed_cards: int, villain_id: int, difficulty: str, hero_id: int) -> List[dict]:
    """
    Obtiene cartas del aspecto basándose en qué cartas aparecen más en mazos ganadores
    contra el villano especificado. Si no hay datos históricos, usa cartas aleatorias del aspecto.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener mazos ganadores contra este villano con el mismo héroe y aspecto
        cursor.execute('''
            SELECT d.cards
            FROM game_configurations gc
            JOIN decks d ON gc.deck_id = d.id
            WHERE gc.villain_id = ?
                AND gc.difficulty = ?
                AND gc.result = 'win'
                AND d.aspect = ?
                AND d.hero_id = ?
        ''', (villain_id, difficulty, aspect, hero_id))
        
        # Contar qué cartas aparecen más frecuentemente en mazos ganadores
        card_counts = {}  # {card_id: {'count': int, 'total_quantity': int, 'name': str, 'card_set': str, 'deck_limit': int}}
        
        for row in cursor.fetchall():
            try:
                deck_cards = json.loads(row["cards"]) if row["cards"] else []
                for card in deck_cards:
                    card_id = card.get("card_id")
                    if not card_id:
                        continue
                    
                    # Verificar que la carta pertenece al aspecto correcto O es básica
                    cursor.execute('''
                        SELECT id, name, aspect, pack_name, deck_limit
                        FROM cards
                        WHERE id = ? 
                            AND (aspect = ? OR aspect = '' OR aspect IS NULL OR aspect = 'basic')
                            AND type != 'alter_ego'
                            AND type != 'alter-ego'
                            AND type != 'hero'
                            AND type != 'villain'
                    ''', (card_id, aspect))
                    
                    card_info = cursor.fetchone()
                    if not card_info:
                        continue
                    
                    quantity = card.get("quantity", 1)
                    
                    if card_id not in card_counts:
                        card_counts[card_id] = {
                            'count': 0,
                            'total_quantity': 0,
                            'name': card_info["name"],
                            'card_set': card_info["pack_name"] or "Unknown",
                            'deck_limit': card_info["deck_limit"] or 3
                        }
                    
                    card_counts[card_id]['count'] += 1
                    card_counts[card_id]['total_quantity'] += quantity
            except (json.JSONDecodeError, KeyError) as e:
                continue
        
        # Ordenar cartas por frecuencia en mazos ganadores
        sorted_cards = sorted(
            card_counts.items(),
            key=lambda x: (x[1]['count'], x[1]['total_quantity']),
            reverse=True
        )
        
        # Seleccionar las cartas más frecuentes
        winning_cards = []
        for card_id, card_data in sorted_cards[:needed_cards * 2]:  # Obtener más de las necesarias
            deck_limit = card_data['deck_limit']
            # Usar la cantidad promedio que aparece en mazos ganadores, pero limitada por deck_limit
            avg_quantity = max(1, min(3, card_data['total_quantity'] // max(1, card_data['count'])))
            quantity = min(deck_limit, avg_quantity)
            
            winning_cards.append({
                "card_id": card_id,
                "card_name": card_data['name'],
                "card_set": card_data['card_set'],
                "quantity": quantity
            })
        
        # Si tenemos suficientes cartas de mazos ganadores, usarlas
        if len(winning_cards) >= needed_cards:
            # Ajustar cantidades para llegar exactamente a needed_cards
            selected_cards = []
            current_total = 0
            for card in winning_cards:
                if current_total >= needed_cards:
                    break
                card_quantity = min(card["quantity"], needed_cards - current_total)
                if card_quantity > 0:
                    card["quantity"] = card_quantity
                    selected_cards.append(card)
                    current_total += card_quantity
            conn.close()
            return selected_cards
        
        # Si no hay suficientes cartas de mazos ganadores, completar con cartas aleatorias del aspecto
        used_card_ids = [card["card_id"] for card in winning_cards]
        placeholders = ','.join(['?'] * len(used_card_ids)) if used_card_ids else 'NULL'
        
        # Obtener cartas del aspecto Y cartas básicas
        # Las cartas básicas siempre se pueden meter en cualquier mazo
        query = f'''
            SELECT id, name, cost, type, aspect, pack_name, quantity, deck_limit
            FROM cards 
            WHERE (aspect = ? OR aspect = '' OR aspect IS NULL OR aspect = 'basic')
            AND type != 'alter_ego'
            AND type != 'alter-ego'
            AND type != 'hero'
            AND type != 'villain'
            {'AND id NOT IN (' + placeholders + ')' if used_card_ids else ''}
            ORDER BY 
                CASE 
                    WHEN aspect = ? THEN 0  -- Priorizar cartas del aspecto
                    WHEN aspect = '' OR aspect IS NULL OR aspect = 'basic' THEN 1  -- Luego básicas
                    ELSE 2
                END,
                RANDOM()
            LIMIT ?
        '''
        
        params = [aspect, aspect]  # aspect aparece dos veces: una para WHERE y otra para CASE
        if used_card_ids:
            params.extend(used_card_ids)
        params.append(needed_cards * 3)  # Obtener más cartas para tener opciones
        
        cursor.execute(query, params)
        
        cards = winning_cards.copy()
        current_total = sum(card.get("quantity", 1) for card in cards)
        target_total = needed_cards
        
        for row in cursor.fetchall():
            if current_total >= target_total:
                break
            
            # Verificar que no esté ya en la lista
            if any(card["card_id"] == row["id"] for card in cards):
                continue
            
            deck_limit = row["deck_limit"] or 3
            quantity = min(random.randint(1, min(deck_limit, 3)), target_total - current_total)
            
            if quantity > 0:
                cards.append({
                    "card_id": row["id"],
                    "card_name": row["name"],
                    "card_set": row["pack_name"] or "Unknown",
                    "quantity": quantity
                })
                current_total += quantity
        
        conn.close()
        return cards
    except Exception as e:
        print(f"Error obteniendo cartas del aspecto (usando fallback): {e}")
        # Fallback: obtener cartas aleatorias del aspecto
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            # Fallback: obtener cartas del aspecto Y básicas
            # Priorizar cartas del aspecto, luego básicas
            cursor.execute('''
                SELECT id, name, cost, type, aspect, pack_name, quantity, deck_limit
                FROM cards 
                WHERE (aspect = ? OR aspect = '' OR aspect IS NULL OR aspect = 'basic')
                AND type != 'alter_ego'
                AND type != 'alter-ego'
                AND type != 'hero'
                AND type != 'villain'
                ORDER BY 
                    CASE 
                        WHEN aspect = ? THEN 0  -- Priorizar cartas del aspecto
                        WHEN aspect = '' OR aspect IS NULL OR aspect = 'basic' THEN 1  -- Luego básicas
                        ELSE 2
                    END,
                    RANDOM()
                LIMIT ?
            ''', (aspect, aspect, needed_cards * 3))
            
            cards = []
            current_total = 0
            target_total = needed_cards
            
            for row in cursor.fetchall():
                if current_total >= target_total:
                    break
                
                deck_limit = row["deck_limit"] or 3
                quantity = min(random.randint(1, min(deck_limit, 3)), target_total - current_total)
                
                if quantity > 0:
                    cards.append({
                        "card_id": row["id"],
                        "card_name": row["name"],
                        "card_set": row["pack_name"] or "Unknown",
                        "quantity": quantity
                    })
                    current_total += quantity
            
            conn.close()
            return cards
        except Exception as e2:
            print(f"Error en fallback: {e2}")
            return []

def get_hero_name(hero_id: int) -> Optional[str]:
    """Obtiene el nombre del héroe por su ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM cards WHERE id = ? AND type = "hero"', (hero_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result["name"] if result else None
    except Exception as e:
        print(f"Error obteniendo nombre del héroe: {e}")
        return None

@router.post("/recommendations/deck", response_model=dict, status_code=200)
async def generate_deck_for_villain(
    request_data: DeckGenerationRequest,
    x_auth0_id: Optional[str] = Header(None, alias="X-Auth0-ID")
):
    """
    Genera un mazo optimizado para un villano específico usando inteligencia artificial
    
    Request Body:
    {
        "villain_id": 994808,
        "difficulty": "normal",  // "normal" o "expert"
        "patches": []  // Opcional: array de parches disponibles (por ahora vacío)
    }
    
    Response:
    {
        "deck": {
            "id": null,
            "name": "Mazo optimizado para Rhino",
            "description": "Mazo generado por IA para enfrentar a Rhino en dificultad normal",
            "hero_name": "Spider-Man",
            "hero_id": 1,
            "aspect": "aggression",
            "cards": [...],
            "creator_name": null,
            "created_at": null,
            "updated_at": null,
            "favorite_count": 0
        },
        "message": "Mazo generado exitosamente"
    }
    """
    # Validar autenticación
    if not x_auth0_id:
        raise HTTPException(
            status_code=401,
            detail="Header X-Auth0-ID requerido"
        )
    
    # Validar difficulty
    if request_data.difficulty not in ['normal', 'expert']:
        raise HTTPException(
            status_code=400,
            detail="Dificultad inválida. Debe ser 'normal' o 'expert'"
        )
    
    # Validar que el villano existe
    villain_name = get_villain_name(request_data.villain_id)
    if not villain_name:
        raise HTTPException(
            status_code=404,
            detail=f"Villano con ID {request_data.villain_id} no encontrado"
        )
    
    # Obtener el mejor héroe/aspecto para este villano
    best_combination = get_best_hero_aspect_for_villain(request_data.villain_id, request_data.difficulty)
    
    if not best_combination:
        raise HTTPException(
            status_code=503,
            detail="No se pudo determinar un héroe/aspecto óptimo. El modelo de IA puede no estar disponible o no hay suficientes datos."
        )
    
    hero_id = best_combination["hero_id"]
    aspect = best_combination["aspect"]
    
    # Obtener nombre del héroe
    hero_name = get_hero_name(hero_id)
    if not hero_name:
        raise HTTPException(
            status_code=500,
            detail=f"Héroe con ID {hero_id} no encontrado"
        )
    
    # Obtener cartas del héroe
    hero_cards = get_hero_specific_cards(hero_id)
    
    # Calcular cuántas cartas adicionales necesitamos
    current_total = sum(card.get("quantity", 1) for card in hero_cards)
    target_total = random.randint(40, 50)
    needed_cards = max(0, target_total - current_total)
    
    # Obtener cartas del aspecto para completar el mazo
    # Usar datos históricos de mazos ganadores contra este villano
    aspect_cards = get_aspect_cards_for_deck(aspect, needed_cards, request_data.villain_id, request_data.difficulty, hero_id)
    
    # Combinar cartas del héroe con las del aspecto
    all_cards = hero_cards.copy()
    current_total = sum(card.get("quantity", 1) for card in all_cards)
    
    # Añadir cartas del aspecto hasta llegar al objetivo
    for card in aspect_cards:
        if current_total >= target_total:
            break
        
        card_quantity = card.get("quantity", 1)
        if current_total + card_quantity <= target_total:
            all_cards.append(card)
            current_total += card_quantity
        elif current_total < target_total:
            remaining = target_total - current_total
            if remaining > 0:
                card["quantity"] = remaining
                all_cards.append(card)
                current_total += remaining
            break
    
    # Asegurar que tenemos al menos 40 cartas
    final_total = sum(card.get("quantity", 1) for card in all_cards)
    if final_total < 40:
        # Añadir más cartas del aspecto si es necesario
        additional_needed = 40 - final_total
        additional_cards = get_aspect_cards_for_deck(aspect, additional_needed)
        for card in additional_cards:
            if final_total >= 40:
                break
            card_quantity = min(card.get("quantity", 1), 40 - final_total)
            if card_quantity > 0:
                card["quantity"] = card_quantity
                all_cards.append(card)
                final_total += card_quantity
    
    # Generar nombre y descripción del mazo
    difficulty_text = "normal" if request_data.difficulty == "normal" else "experto"
    deck_name = f"Mazo optimizado para {villain_name}"
    deck_description = f"Mazo generado por IA (SVM) para enfrentar a {villain_name} en dificultad {difficulty_text}. Héroe: {hero_name}, Aspecto: {aspect}."
    
    # Construir respuesta
    deck = {
        "id": None,
        "name": deck_name,
        "description": deck_description,
        "hero_name": hero_name,
        "hero_id": hero_id,
        "aspect": aspect,
        "cards": all_cards,
        "creator_name": None,
        "created_at": None,
        "updated_at": None,
        "favorite_count": 0
    }
    
    return {
        "deck": deck,
        "message": "Mazo generado exitosamente"
    }

