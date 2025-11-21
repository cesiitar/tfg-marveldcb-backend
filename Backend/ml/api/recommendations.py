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
_model_data = None  # Cache para el formato del modelo (con model y feature_names)

def load_model():
    """
    Carga el modelo entrenado (con cache)
    Soporta formato antiguo (solo modelo) y nuevo (diccionario con model y feature_names)
    NOTA: Ya no se usa top_cards - las cartas se seleccionan dinámicamente
    """
    global _model, _model_data
    if _model_data is None:
        if not os.path.exists(MODEL_PATH):
            return None
        with open(MODEL_PATH, 'rb') as f:
            data = pickle.load(f)
        
        # Si es el nuevo formato (diccionario)
        if isinstance(data, dict) and 'model' in data:
            _model_data = data
            _model = data['model']
        else:
            # Formato antiguo (solo el modelo)
            _model = data
            _model_data = {'model': _model, 'feature_names': None}
    
    return _model_data['model'] if _model_data else _model

def get_model_data():
    """
    Obtiene los datos completos del modelo (modelo + feature_names)
    """
    global _model_data
    if _model_data is None:
        load_model()  # Esto carga _model_data
    return _model_data

def get_average_deck_features(hero_id: int, aspect: str, villain_id: int, difficulty: str) -> List[float]:
    """
    Calcula las características agregadas promedio para una combinación hero/aspect/villain/difficulty.
    Si no hay datos históricos, usa valores por defecto razonables.
    
    Returns:
        Lista con [avg_cost, event_ratio, ally_ratio, upgrade_ratio, support_ratio]
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscar mazos ganadores con esta combinación
    cursor.execute('''
        SELECT d.cards
        FROM game_configurations gc
        JOIN decks d ON gc.deck_id = d.id
        WHERE gc.villain_id = ?
            AND gc.difficulty = ?
            AND gc.result = 'win'
            AND d.hero_id = ?
            AND d.aspect = ?
            AND d.cards IS NOT NULL
        LIMIT 10
    ''', (villain_id, difficulty, hero_id, aspect))
    
    decks = cursor.fetchall()
    
    if not decks:
        # Si no hay datos, usar valores por defecto razonables
        conn.close()
        return [2.0, 0.4, 0.2, 0.2, 0.2]  # avg_cost=2.0, event=40%, ally=20%, upgrade=20%, support=20%
    
    # Calcular promedios
    total_avg_cost = 0.0
    total_event_ratio = 0.0
    total_ally_ratio = 0.0
    total_upgrade_ratio = 0.0
    total_support_ratio = 0.0
    valid_decks = 0
    
    for deck_row in decks:
        try:
            deck_cards = json.loads(deck_row['cards']) if deck_row['cards'] else []
            if not deck_cards:
                continue
            
            avg_cost = 0.0
            event_count = 0
            ally_count = 0
            upgrade_count = 0
            support_count = 0
            total_cards = 0
            
            for card in deck_cards:
                card_id = card.get('card_id')
                quantity = card.get('quantity', 1)
                total_cards += quantity
                
                if card_id:
                    cursor.execute('SELECT cost, type FROM cards WHERE id = ?', (card_id,))
                    card_info = cursor.fetchone()
                    if card_info:
                        cost = card_info[0] or 0
                        card_type = (card_info[1] or '').lower()
                        avg_cost += cost * quantity
                        
                        if 'event' in card_type:
                            event_count += quantity
                        elif 'ally' in card_type:
                            ally_count += quantity
                        elif 'upgrade' in card_type or 'attachment' in card_type:
                            upgrade_count += quantity
                        elif 'support' in card_type:
                            support_count += quantity
            
            if total_cards > 0:
                total_avg_cost += avg_cost / total_cards
                total_event_ratio += event_count / total_cards
                total_ally_ratio += ally_count / total_cards
                total_upgrade_ratio += upgrade_count / total_cards
                total_support_ratio += support_count / total_cards
                valid_decks += 1
        except:
            continue
    
    conn.close()
    
    if valid_decks == 0:
        return [2.0, 0.4, 0.2, 0.2, 0.2]  # Valores por defecto
    
    return [
        total_avg_cost / valid_decks,
        total_event_ratio / valid_decks,
        total_ally_ratio / valid_decks,
        total_upgrade_ratio / valid_decks,
        total_support_ratio / valid_decks
    ]

# Esquemas de datos
class DeckData(BaseModel):
    hero_id: int
    aspect: str  # 'aggression', 'justice', 'leadership', 'protection', 'pool'
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
    valid_aspects = ['aggression', 'justice', 'leadership', 'protection', 'pool']
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
        'protection': 3,
        'pool': 4
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
        
        # Obtener características agregadas promedio
        avg_features = get_average_deck_features(
            deck_data.hero_id, deck_data.aspect, deck_data.villain_id, deck_data.difficulty
        )
        
        # Preparar features: [hero_id, aspect_encoded, villain_id, difficulty_encoded, avg_cost, event_ratio, ally_ratio, upgrade_ratio, support_ratio]
        features = np.array([[
            deck_data.hero_id,
            aspect_encoded,
            deck_data.villain_id,
            difficulty_encoded,
            avg_features[0],  # avg_cost
            avg_features[1],  # event_ratio
            avg_features[2],  # ally_ratio
            avg_features[3],  # upgrade_ratio
            avg_features[4]   # support_ratio
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
            # Obtener características agregadas promedio para este villano
            avg_features = get_average_deck_features(
                deck_data.hero_id, deck_data.aspect, villain['id'], deck_data.difficulty
            )
            
            features = np.array([[
                deck_data.hero_id,
                aspect_encoded,
                villain['id'],
                difficulty_encoded,
                avg_features[0],  # avg_cost
                avg_features[1],  # event_ratio
                avg_features[2],  # ally_ratio
                avg_features[3],  # upgrade_ratio
                avg_features[4]   # support_ratio
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
        aspect_map = {'aggression': 0, 'justice': 1, 'leadership': 2, 'protection': 3, 'pool': 4}
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
            
            # Obtener características agregadas promedio para esta combinación
            avg_features = get_average_deck_features(hero_id, aspect, villain_id, difficulty)
            
            # Preparar features para el SVM: [hero_id, aspect, villain_id, difficulty, avg_cost, event_ratio, ally_ratio, upgrade_ratio, support_ratio]
            features = np.array([[
                hero_id,
                aspect_map[aspect],
                villain_id,
                difficulty_encoded,
                avg_features[0],  # avg_cost
                avg_features[1],  # event_ratio
                avg_features[2],  # ally_ratio
                avg_features[3],  # upgrade_ratio
                avg_features[4]   # support_ratio
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
                "quantity": quantity,
                "type": row["type"],
                "clase": row["aspect"] or "hero",
                "set": hero_pack_name or "Unknown"
            })
        
        conn.close()
        return hero_cards
    except Exception as e:
        print(f"Error obteniendo cartas del héroe: {e}")
        return []

def get_aspect_cards_for_deck(aspect: str, needed_cards: int, villain_id: int, difficulty: str, hero_id: int) -> List[dict]:
    """
    El SVM (IA) decide 100% qué cartas elegir, igual que con los héroes.
    
    CÓMO FUNCIONA (100% SVM):
    1. Obtener todas las cartas candidatas (del aspecto o básicas) que aparecen en mazos ganadores
    2. Para cada carta, buscar en qué mazos aparece (contra este villano)
    3. Usar el SVM para predecir la probabilidad de victoria de esos mazos
    4. El SVM decide 100% - seleccionar las cartas que aparecen en mazos con mayor probabilidad según el SVM
    
    CARTAS DEL ASPECTO: Buscar en mazos ganadores con ese aspecto (diferentes héroes)
    CARTAS BÁSICAS: Buscar en TODOS los mazos ganadores (cualquier aspecto/héroe)
    """
    model = load_model()
    if not model:
        return get_aspect_cards_fallback(aspect, needed_cards)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        aspect_map = {'aggression': 0, 'justice': 1, 'leadership': 2, 'protection': 3, 'pool': 4}
        difficulty_encoded = 0 if difficulty == 'normal' else 1
        
        print(f"🤖 SVM (IA) analizando cartas candidatas para {aspect} contra este villano...")
        
        # 1. Obtener todas las cartas candidatas (del aspecto o básicas) que aparecen en mazos ganadores
        # CARTAS DEL ASPECTO: de mazos ganadores con ese aspecto
        cursor.execute('''
            SELECT d.id, d.cards, d.hero_id, d.aspect
            FROM game_configurations gc
            JOIN decks d ON gc.deck_id = d.id
            WHERE gc.villain_id = ?
                AND gc.difficulty = ?
                AND gc.result = 'win'
                AND d.aspect = ?
                AND d.cards IS NOT NULL
        ''', (villain_id, difficulty, aspect))
        
        aspect_winning_decks = cursor.fetchall()
        
        # CARTAS BÁSICAS: de TODOS los mazos ganadores
        cursor.execute('''
            SELECT d.id, d.cards, d.hero_id, d.aspect
            FROM game_configurations gc
            JOIN decks d ON gc.deck_id = d.id
            WHERE gc.villain_id = ?
                AND gc.difficulty = ?
                AND gc.result = 'win'
                AND d.cards IS NOT NULL
        ''', (villain_id, difficulty))
        
        all_winning_decks = cursor.fetchall()
        
        # Extraer cartas únicas del aspecto
        aspect_card_ids = set()
        aspect_decks_info = {}  # {card_id: [{'hero_id': int, 'aspect': str}, ...]}
        
        for deck_row in aspect_winning_decks:
            try:
                deck_cards = json.loads(deck_row['cards']) if deck_row['cards'] else []
                for card in deck_cards:
                    card_id = card.get('card_id')
                    if card_id:
                        aspect_card_ids.add(card_id)
                        if card_id not in aspect_decks_info:
                            aspect_decks_info[card_id] = []
                        aspect_decks_info[card_id].append({
                            'hero_id': deck_row['hero_id'],
                            'aspect': deck_row['aspect']
                        })
            except:
                continue
        
        # Extraer cartas básicas únicas
        basic_card_ids = set()
        basic_decks_info = {}  # {card_id: [{'hero_id': int, 'aspect': str}, ...]}
        
        for deck_row in all_winning_decks:
            try:
                deck_cards = json.loads(deck_row['cards']) if deck_row['cards'] else []
                for card in deck_cards:
                    card_id = card.get('card_id')
                    if card_id:
                        # Verificar que es básica
                        cursor.execute('''
                            SELECT aspect FROM cards WHERE id = ?
                        ''', (card_id,))
                        card_aspect_row = cursor.fetchone()
                        if card_aspect_row and (not card_aspect_row['aspect'] or card_aspect_row['aspect'] == 'basic'):
                            basic_card_ids.add(card_id)
                            if card_id not in basic_decks_info:
                                basic_decks_info[card_id] = []
                            basic_decks_info[card_id].append({
                                'hero_id': deck_row['hero_id'],
                                'aspect': deck_row['aspect']
                            })
            except:
                continue
        
        # Obtener información de las cartas
        all_candidate_cards = []
        
        if aspect_card_ids:
            placeholders = ','.join(['?'] * len(aspect_card_ids))
            cursor.execute(f'''
                SELECT id, name, aspect, pack_name, deck_limit, type, cost
                FROM cards
                WHERE id IN ({placeholders})
                    AND aspect = ?
            ''', list(aspect_card_ids) + [aspect])
            all_candidate_cards.extend(cursor.fetchall())
        
        if basic_card_ids:
            placeholders = ','.join(['?'] * len(basic_card_ids))
            cursor.execute(f'''
                SELECT id, name, aspect, pack_name, deck_limit, type, cost
                FROM cards
                WHERE id IN ({placeholders})
                    AND (aspect = '' OR aspect IS NULL OR aspect = 'basic')
            ''', list(basic_card_ids))
            all_candidate_cards.extend(cursor.fetchall())
        
        if not all_candidate_cards:
            conn.close()
            return get_aspect_cards_fallback(aspect, needed_cards)
        
        print(f"   📊 Encontradas {len(aspect_card_ids)} cartas del aspecto y {len(basic_card_ids)} básicas")
        
        # 2. Para cada carta, usar el SVM para predecir probabilidad
        card_scores = {}  # {card_id: {'svm_prob': float, 'name': str, 'card_set': str, 'deck_limit': int, 'type': str, 'aspect': str}}
        
        for card_row in all_candidate_cards:
            card_id = card_row['id']
            card_aspect = card_row['aspect'] or 'basic'
            
            # Obtener mazos que contienen esta carta
            if card_aspect == 'basic':
                decks_with_card = basic_decks_info.get(card_id, [])
            else:
                decks_with_card = aspect_decks_info.get(card_id, [])
            
            if not decks_with_card:
                # Si la carta no aparece en ningún mazo, usar probabilidad base con características promedio
                avg_features = get_average_deck_features(hero_id, aspect, villain_id, difficulty)
                svm_prob = model.predict_proba(np.array([[
                    hero_id, aspect_map[aspect], villain_id, difficulty_encoded,
                    avg_features[0], avg_features[1], avg_features[2], avg_features[3], avg_features[4]
                ]]))[0][1]
            else:
                # Calcular probabilidad promedio según el SVM para mazos que contienen esta carta
                svm_probs = []
                for deck_info in decks_with_card:
                    deck_hero_id = deck_info['hero_id']
                    deck_aspect = deck_info['aspect']
                    deck_aspect_encoded = aspect_map.get(deck_aspect, 0)
                    
                    # Obtener características promedio para este deck
                    avg_features = get_average_deck_features(deck_hero_id, deck_aspect, villain_id, difficulty)
                    
                    features = np.array([[
                        deck_hero_id,
                        deck_aspect_encoded,
                        villain_id,
                        difficulty_encoded,
                        avg_features[0],  # avg_cost
                        avg_features[1],  # event_ratio
                        avg_features[2],  # ally_ratio
                        avg_features[3],  # upgrade_ratio
                        avg_features[4]   # support_ratio
                    ]])
                    prob = model.predict_proba(features)[0][1]
                    svm_probs.append(prob)
                
                svm_prob = sum(svm_probs) / len(svm_probs) if svm_probs else 0.0
            
            card_scores[card_id] = {
                'svm_prob': svm_prob,
                'name': card_row['name'],
                'card_set': card_row['pack_name'] or "Unknown",
                'deck_limit': card_row['deck_limit'] or 3,
                'type': card_row['type'],
                'aspect': card_aspect
            }
        
        # 3. Ordenar cartas por probabilidad del SVM (mayor a menor) - EL SVM DECIDE 100%
        sorted_cards = sorted(
            card_scores.items(),
            key=lambda x: x[1]['svm_prob'],
            reverse=True
        )
        
        # 4. Seleccionar las cartas con mayor probabilidad según el SVM
        selected_cards = []
        current_total = 0
        
        for card_id, card_data in sorted_cards:
            if current_total >= needed_cards:
                break
            
            deck_limit = card_data['deck_limit']
            # Cantidad basada en probabilidad del SVM (mayor probabilidad = más copias)
            if card_data['svm_prob'] > 0.7:
                quantity = min(3, deck_limit)
            elif card_data['svm_prob'] > 0.5:
                quantity = min(2, deck_limit)
            else:
                quantity = 1
            
            quantity = min(quantity, needed_cards - current_total)
            
            if quantity > 0:
                selected_cards.append({
                    "card_id": card_id,
                    "card_name": card_data['name'],
                    "card_set": card_data['card_set'],
                    "quantity": quantity,
                    "type": card_data['type'],
                    "clase": card_data['aspect'],
                    "set": card_data['card_set']
                })
                current_total += quantity
        
        conn.close()
        
        if len(selected_cards) < needed_cards:
            additional = get_aspect_cards_fallback(aspect, needed_cards - current_total)
            selected_cards.extend(additional)
        
        print(f"✅ SVM (IA) seleccionó {len(selected_cards)} cartas (100% decisión del SVM)")
        return selected_cards[:needed_cards] if len(selected_cards) > needed_cards else selected_cards
        
    except Exception as e:
        print(f"Error obteniendo cartas con SVM: {e}")
        import traceback
        traceback.print_exc()
        return get_aspect_cards_fallback(aspect, needed_cards)

def get_aspect_cards_fallback(aspect: str, needed_cards: int) -> List[dict]:
    """
    Función fallback para obtener cartas aleatorias del aspecto si el SVM falla
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
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
                    WHEN aspect = ? THEN 0
                    WHEN aspect = '' OR aspect IS NULL OR aspect = 'basic' THEN 1
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
                    "quantity": quantity,
                    "type": row["type"],
                    "clase": row["aspect"] or 'basic',
                    "set": row["pack_name"] or "Unknown"
                })
                current_total += quantity
        
        conn.close()
        return cards
    except Exception as e:
        print(f"Error en fallback: {e}")
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
    
    # Calcular probabilidad de victoria del mazo completo usando el SVM
    model = load_model()
    win_probability = None
    if model:
        aspect_map = {'aggression': 0, 'justice': 1, 'leadership': 2, 'protection': 3, 'pool': 4}
        difficulty_encoded = 0 if request_data.difficulty == 'normal' else 1
        
        # Obtener características agregadas promedio para este mazo
        avg_features = get_average_deck_features(hero_id, aspect, request_data.villain_id, request_data.difficulty)
        
        features = np.array([[
            hero_id,
            aspect_map[aspect],
            request_data.villain_id,
            difficulty_encoded,
            avg_features[0],  # avg_cost
            avg_features[1],  # event_ratio
            avg_features[2],  # ally_ratio
            avg_features[3],  # upgrade_ratio
            avg_features[4]   # support_ratio
        ]])
        
        win_probability = float(model.predict_proba(features)[0][1])
        print(f"🎯 Probabilidad de victoria del mazo (SVM): {win_probability:.2%}")
    
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
        "favorite_count": 0,
        "win_probability": win_probability  # Probabilidad de victoria según el SVM
    }
    
    return {
        "deck": deck,
        "message": "Mazo generado exitosamente",
        "win_probability": win_probability  # También en el nivel superior para fácil acceso
    }

