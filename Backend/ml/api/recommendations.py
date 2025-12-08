from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel
from typing import List, Optional
import pickle
import os
import numpy as np
import sqlite3
import json
import random

# Importar utilidades centralizadas de base de datos
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from db_utils import get_db_connection

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
class DeckGenerationRequest(BaseModel):
    villain_id: int
    difficulty: str  # 'normal' o 'expert'
    patches: Optional[List[str]] = []  # Por ahora vacío, se implementará después
    max_decks: Optional[int] = 3  # Número máximo de mazos a generar (por defecto 3, máximo 4)

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

def get_top_hero_aspect_combinations(villain_id: int, difficulty: str, top_n: int = 3) -> List[dict]:
    """
    Obtiene las mejores N combinaciones héroe/aspecto contra el villano, ordenadas por probabilidad del SVM.
    
    Returns: Lista de diccionarios con las mejores combinaciones ordenadas por win_probability (mayor a menor)
    """
    model = load_model()
    if not model:
        return []

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener combinaciones que tienen al menos 1 partida contra este villano
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
            return []
        
        # Solo considerar combinaciones que han GANADO al menos una vez
        winning_combinations = [row for row in historical_combinations if row['win_rate'] > 0]
        
        if not winning_combinations:
            return []
        
        # Calcular probabilidad del SVM para cada combinación
        aspect_map = {'aggression': 0, 'justice': 1, 'leadership': 2, 'protection': 3, 'pool': 4}
        difficulty_encoded = 0 if difficulty == 'normal' else 1
        
        combinations_with_prob = []
        
        for row in winning_combinations:
            hero_id = row["hero_id"]
            aspect = row["aspect"]
            win_rate = row["win_rate"]
            total_games = row["total_games"]
            
            # Obtener características agregadas promedio para esta combinación
            avg_features = get_average_deck_features(hero_id, aspect, villain_id, difficulty)
            
            # Preparar features para el SVM
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
            
            # El SVM predice la probabilidad
            svm_prob = model.predict_proba(features)[0][1]
            
            combinations_with_prob.append({
                "hero_id": hero_id,
                "aspect": aspect,
                "win_probability": float(svm_prob),
                "win_rate": float(win_rate),
                "total_games": int(total_games),
                "wins": int(row["wins"])
            })
        
        # Ordenar por probabilidad del SVM (mayor a menor) y devolver las top N
        combinations_with_prob.sort(key=lambda x: x['win_probability'], reverse=True)
        
        return combinations_with_prob[:top_n]
    except Exception as e:
        print(f"Error obteniendo top combinaciones héroe/aspecto: {e}")
        import traceback
        traceback.print_exc()
        return []

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
        
        # Extraer TODAS las cartas de los mazos ganadores primero (sin filtrar por aspecto todavía)
        all_deck_card_ids = set()
        temp_decks_info = {}  # {card_id: [{'hero_id': int, 'aspect': str}, ...]}
        
        for deck_row in aspect_winning_decks:
            try:
                deck_cards = json.loads(deck_row['cards']) if deck_row['cards'] else []
                for card in deck_cards:
                    card_id = card.get('card_id')
                    if card_id:
                        all_deck_card_ids.add(card_id)
                        if card_id not in temp_decks_info:
                            temp_decks_info[card_id] = []
                        temp_decks_info[card_id].append({
                            'hero_id': deck_row['hero_id'],
                            'aspect': deck_row['aspect']
                        })
            except:
                continue
        
        # Ahora verificar qué cartas son realmente del aspecto correcto (una sola consulta)
        aspect_card_ids = set()
        aspect_decks_info = {}
        
        if all_deck_card_ids:
            placeholders = ','.join(['?'] * len(all_deck_card_ids))
            cursor.execute(f'''
                SELECT id, aspect FROM cards WHERE id IN ({placeholders})
            ''', list(all_deck_card_ids))
            
            for row in cursor.fetchall():
                card_id = row['id']
                card_aspect = row['aspect']
                if card_aspect == aspect:
                    # Solo añadir si es del aspecto correcto
                    aspect_card_ids.add(card_id)
                    if card_id in temp_decks_info:
                        aspect_decks_info[card_id] = temp_decks_info[card_id]
        
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
            # Ya verificamos que son del aspecto correcto, así que solo necesitamos el filtro por ID
            cursor.execute(f'''
                SELECT id, name, aspect, pack_name, deck_limit, type, cost
                FROM cards
                WHERE id IN ({placeholders})
            ''', list(aspect_card_ids))
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
        print(f"   📊 Mazos ganadores con aspecto {aspect}: {len(aspect_winning_decks)}")
        
        if len(aspect_winning_decks) == 0:
            print(f"   ⚠️  No hay mazos ganadores con aspecto {aspect} contra este villano. Usando fallback.")
        
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
        
        # Verificar si necesitamos más copias (no cartas únicas, sino copias totales)
        remaining_copies = needed_cards - current_total
        if remaining_copies > 0:
            print(f"   ⚠️  Solo se seleccionaron {current_total} copias de cartas, se necesitan {needed_cards}. Usando fallback para {remaining_copies} copias adicionales.")
            additional = get_aspect_cards_fallback(aspect, remaining_copies)
            selected_cards.extend(additional)
            total_additional_copies = sum(c.get('quantity', 1) for c in additional)
            print(f"   📝 Fallback añadió {len(additional)} cartas adicionales ({total_additional_copies} copias totales)")
        
        # Verificar que todas las cartas seleccionadas sean del aspecto correcto o básicas
        print(f"   📋 Cartas seleccionadas por el SVM:")
        for card in selected_cards[:5]:  # Mostrar solo las primeras 5
            print(f"      - {card['card_name']} ({card.get('clase', 'unknown')})")
        if len(selected_cards) > 5:
            print(f"      ... y {len(selected_cards) - 5} más")
        
        # Asegurar que no excedamos el número de copias necesarias
        final_cards = []
        final_total = 0
        for card in selected_cards:
            if final_total >= needed_cards:
                break
            card_quantity = card.get('quantity', 1)
            remaining = needed_cards - final_total
            if card_quantity > remaining:
                card = card.copy()
                card['quantity'] = remaining
            final_cards.append(card)
            final_total += card.get('quantity', 1)
        
        print(f"✅ SVM (IA) seleccionó {len(final_cards)} cartas ({final_total} copias totales)")
        return final_cards
        
    except Exception as e:
        print(f"Error obteniendo cartas con SVM: {e}")
        import traceback
        traceback.print_exc()
        return get_aspect_cards_fallback(aspect, needed_cards)

def get_aspect_cards_fallback(aspect: str, needed_cards: int) -> List[dict]:
    """
    Función fallback para obtener cartas aleatorias del aspecto si el SVM falla o no hay suficientes datos.
    
    NOTA: Este fallback se usa cuando:
    - No hay suficientes mazos ganadores con ese aspecto contra el villano
    - El SVM no puede seleccionar suficientes cartas
    - Hay un error en el proceso de selección
    
    Selecciona cartas aleatorias del aspecto especificado o básicas.
    """
    print(f"   🔄 Usando fallback: seleccionando cartas aleatorias de {aspect} (no hay suficientes datos históricos)")
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
                id
            LIMIT ?
        ''', (aspect, aspect, needed_cards * 3))
        
        cards = []
        current_total = 0
        target_total = needed_cards
        
        for row in cursor.fetchall():
            if current_total >= target_total:
                break
            
            deck_limit = row["deck_limit"] or 3
            # Hacer determinista: usar el ID de la carta para decidir cantidad (1, 2 o 3)
            # Esto asegura que la misma carta siempre tenga la misma cantidad
            card_hash = hash(row["id"]) % 3  # 0, 1 o 2
            base_quantity = min(deck_limit, 3)
            if base_quantity >= 3:
                quantity = card_hash + 1  # 1, 2 o 3
            elif base_quantity == 2:
                quantity = min(card_hash + 1, 2)  # 1 o 2
            else:
                quantity = 1
            quantity = min(quantity, target_total - current_total)
            
            if quantity > 0:
                # Determinar la clase correcta de la carta
                card_aspect = row["aspect"]
                if not card_aspect or card_aspect == '' or card_aspect == 'basic':
                    card_clase = 'basic'
                else:
                    card_clase = card_aspect
                
                cards.append({
                    "card_id": row["id"],
                    "card_name": row["name"],
                    "card_set": row["pack_name"] or "Unknown",
                    "quantity": quantity,
                    "type": row["type"],
                    "clase": card_clase,
                    "set": row["pack_name"] or "Unknown"
                })
                current_total += quantity
        
        conn.close()
        print(f"   📝 Fallback seleccionó {len(cards)} cartas aleatorias ({sum(c['quantity'] for c in cards)} copias totales)")
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

def generate_single_deck(hero_id: int, aspect: str, villain_id: int, difficulty: str, villain_name: str) -> Optional[dict]:
    """
    Genera un mazo individual para una combinación hero/aspect específica.
    
    Returns: Diccionario con el mazo generado o None si hay error
    """
    try:
        # Obtener nombre del héroe
        hero_name = get_hero_name(hero_id)
        if not hero_name:
            return None
        
        # Obtener cartas del héroe
        hero_cards = get_hero_specific_cards(hero_id)
        
        # Calcular cuántas cartas adicionales necesitamos
        # Hacer determinista: usar hash del villano+heroe para elegir entre 40-50
        # Esto asegura que el mismo villano+heroe siempre genere el mismo número de cartas
        current_total = sum(card.get("quantity", 1) for card in hero_cards)
        # Usar hash determinista para elegir entre 40-50
        hash_value = hash((villain_id, hero_id, difficulty)) % 11  # 0-10 para 40-50
        target_total = 40 + hash_value  # Entre 40 y 50
        needed_cards = max(0, target_total - current_total)
        
        # Obtener cartas del aspecto para completar el mazo
        aspect_cards = get_aspect_cards_for_deck(aspect, needed_cards, villain_id, difficulty, hero_id)
        
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
            additional_cards = get_aspect_cards_for_deck(aspect, additional_needed, villain_id, difficulty, hero_id)
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
            difficulty_encoded = 0 if difficulty == 'normal' else 1
            
            # Obtener características agregadas promedio para este mazo
            avg_features = get_average_deck_features(hero_id, aspect, villain_id, difficulty)
            
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
            
            win_probability = float(model.predict_proba(features)[0][1])
        
        # Generar nombre y descripción del mazo
        difficulty_text = "normal" if difficulty == "normal" else "experto"
        deck_name = f"Mazo optimizado para {villain_name}"
        deck_description = f"Mazo generado por IA (SVM) para enfrentar a {villain_name} en dificultad {difficulty_text}. Héroe: {hero_name}, Aspecto: {aspect}."
        
        # Construir mazo
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
        
        # Añadir win_probability al deck si está disponible
        if win_probability is not None:
            deck["win_probability"] = win_probability
        
        return deck
    except Exception as e:
        print(f"Error generando mazo para {hero_id}/{aspect}: {e}")
        return None

@router.post("/recommendations/deck", response_model=dict, status_code=200)
async def generate_deck_for_villain(
    request_data: DeckGenerationRequest,
    x_auth0_id: Optional[str] = Header(None, alias="X-Auth0-ID")
):
    """
    Genera uno o varios mazos optimizados para un villano específico usando inteligencia artificial
    
    Request Body:
    {
        "villain_id": 994808,
        "difficulty": "normal",  // "normal" o "expert"
        "patches": [],  // Opcional: array de parches disponibles (por ahora vacío)
        "max_decks": 3  // Opcional: número máximo de mazos a generar (por defecto 3, máximo 4). Si hay menos combinaciones disponibles, se devolverán las que haya.
    }
    
    Response:
    {
        "decks": [
            {
                "id": null,
                "name": "Mazo optimizado para Rhino",
                "description": "Mazo generado por IA para enfrentar a Rhino en dificultad normal",
                "hero_name": "Spider-Man",
                "hero_id": 1,
                "aspect": "aggression",
                "cards": [...],
                "win_probability": 0.75,
                "creator_name": null,
                "created_at": null,
                "updated_at": null,
                "favorite_count": 0
            },
            ...
        ],
        "message": "3 mazo(s) generado(s) exitosamente",
        "total_requested": 3,
        "total_generated": 3
    }
    
    Nota: Los mazos están ordenados por win_probability (mayor a menor).
    Si hay menos combinaciones disponibles que las solicitadas, se devolverán las que haya.
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
    
    # Validar max_decks (máximo 4, por defecto 3)
    max_decks = min(request_data.max_decks or 3, 4)  # Máximo 4 mazos
    if max_decks < 1:
        max_decks = 1
    
    # Validar que el villano existe
    villain_name = get_villain_name(request_data.villain_id)
    if not villain_name:
        raise HTTPException(
            status_code=404,
            detail=f"Villano con ID {request_data.villain_id} no encontrado"
        )
    
    # Obtener las mejores N combinaciones héroe/aspecto (puede haber menos de max_decks disponibles)
    top_combinations = get_top_hero_aspect_combinations(request_data.villain_id, request_data.difficulty, top_n=max_decks)
    
    if not top_combinations:
        raise HTTPException(
            status_code=503,
            detail="No se pudo determinar combinaciones héroe/aspecto óptimas. El modelo de IA puede no estar disponible o no hay suficientes datos."
        )
    
    # Generar un mazo para cada combinación disponible
    # Nota: Puede haber menos combinaciones que max_decks si no hay suficientes datos históricos
    generated_decks = []
    for combination in top_combinations:
        deck = generate_single_deck(
            combination["hero_id"],
            combination["aspect"],
            request_data.villain_id,
            request_data.difficulty,
            villain_name
        )
        
        if deck:
            # Asegurar que win_probability esté presente (usar la de la combinación si no está en el deck)
            if "win_probability" not in deck:
                deck["win_probability"] = combination["win_probability"]
            generated_decks.append(deck)
    
    if not generated_decks:
        raise HTTPException(
            status_code=500,
            detail="No se pudieron generar mazos. Intenta de nuevo."
        )
    
    # Ordenar por win_probability (mayor a menor) - aunque ya deberían estar ordenados
    generated_decks.sort(key=lambda d: d.get("win_probability", 0.0), reverse=True)
    
    # Construir respuesta con información sobre cuántos mazos se generaron
    num_decks = len(generated_decks)
    if num_decks < max_decks:
        message = f"{num_decks} mazo(s) generado(s) exitosamente (de {max_decks} solicitados - solo hay {num_decks} combinaciones disponibles)"
    else:
        message = f"{num_decks} mazo(s) generado(s) exitosamente"
    
    response = {
        "decks": generated_decks,
        "message": message,
        "total_requested": max_decks,
        "total_generated": num_decks
    }
    
    return response

