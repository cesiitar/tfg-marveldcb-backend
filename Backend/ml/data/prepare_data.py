import sqlite3
import pandas as pd
import json
from typing import Tuple
import numpy as np
import os
import sys

# Importar utilidades centralizadas de base de datos
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from db_utils import get_db_path, verify_tables_exist

def get_game_data_from_db(db_path: str = None) -> pd.DataFrame:
    """
    Extrae datos de partidas de la base de datos, incluyendo información de cartas
    
    Returns:
        DataFrame con: deck_id, hero_id, aspect, villain_id, difficulty, result, cards (JSON)
    """
    if db_path is None:
        db_path = get_db_path()
    
    # Verificar que las tablas requeridas existan (usando función centralizada)
    verify_tables_exist(['game_configurations', 'decks'])
    
    conn = sqlite3.connect(db_path)
    
    query = """
    SELECT 
        gc.id as game_id,
        gc.deck_id,
        gc.villain_id,
        gc.difficulty,
        gc.result,
        d.hero_id,
        d.aspect,
        d.cards
    FROM game_configurations gc
    JOIN decks d ON gc.deck_id = d.id
    WHERE gc.result IS NOT NULL
        AND d.hero_id IS NOT NULL
        AND d.aspect IS NOT NULL
        AND gc.villain_id IS NOT NULL
        AND d.cards IS NOT NULL
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return df

def get_top_cards_from_winning_decks(df: pd.DataFrame, top_n: int = 30, aspect: str = None, villain_id: int = None) -> list:
    """
    Identifica las cartas más importantes (las que aparecen más en mazos ganadores)
    
    Si se proporciona aspect y villain_id, filtra por esos criterios.
    Si no, calcula top cartas globales (pero solo del aspecto correspondiente o básicas).
    
    Args:
        df: DataFrame con partidas
        top_n: Número de cartas top a retornar
        aspect: Aspecto específico (opcional, para filtrar)
        villain_id: ID del villano específico (opcional, para filtrar)
    
    Returns:
        Lista de card_ids de las top N cartas más importantes
    """
    card_counts = {}  # {card_id: count}
    
    for idx, row in df.iterrows():
        # Filtrar por resultado ganador
        if row['result'] != 'win':
            continue
        
        # Filtrar por aspecto si se proporciona
        if aspect and row['aspect'] != aspect:
            continue
        
        # Filtrar por villano si se proporciona
        if villain_id and row['villain_id'] != villain_id:
            continue
        
        try:
            cards = json.loads(row['cards']) if row['cards'] else []
            for card in cards:
                card_id = card.get('card_id')
                if card_id:
                    card_counts[card_id] = card_counts.get(card_id, 0) + card.get('quantity', 1)
        except:
            continue
    
    # Ordenar por frecuencia y tomar las top N
    sorted_cards = sorted(card_counts.items(), key=lambda x: x[1], reverse=True)
    top_card_ids = [card_id for card_id, count in sorted_cards[:top_n]]
    
    return top_card_ids

def prepare_features(df: pd.DataFrame, top_cards: list = None) -> Tuple[np.ndarray, np.ndarray, list]:
    """
    Prepara features para el modelo SVM usando solo características generales
    
    Features (NO incluye cartas específicas, solo características agregadas):
    - hero_id (numérico)
    - aspect_encoded (aggression=0, justice=1, leadership=2, protection=3, pool=4)
    - villain_id (numérico)
    - difficulty_encoded (normal=0, expert=1)
    - avg_cost: Coste promedio de las cartas del mazo
    - event_ratio: Proporción de eventos
    - ally_ratio: Proporción de aliados
    - upgrade_ratio: Proporción de mejoras
    - support_ratio: Proporción de soportes
    
    NOTA: NO usamos features binarias de cartas específicas porque:
    - Las cartas relevantes dependen del villano y aspecto específicos
    - Hay millones de combinaciones posibles
    - Las "top cartas" se identifican dinámicamente durante la generación de mazos
    
    Target:
    - result_encoded (loss=0, win=1)
    
    Returns:
        X: array de features (n_samples, n_features)
        y: array de resultados (n_samples,)
        feature_names: Lista de nombres de features (para debugging)
    """
    # Codificar aspect
    aspect_map = {
        'aggression': 0,
        'justice': 1,
        'leadership': 2,
        'protection': 3,
        'pool': 4
    }
    df['aspect_encoded'] = df['aspect'].map(aspect_map).fillna(0)
    
    # Codificar difficulty
    df['difficulty_encoded'] = df['difficulty'].map({'normal': 0, 'expert': 1}).fillna(0)
    
    # Codificar result (win=1, loss=0)
    df['result_encoded'] = df['result'].map({'win': 1, 'loss': 0}).fillna(0)
    
    # Preparar features de cartas (SOLO características agregadas, NO cartas específicas)
    features_list = []
    feature_names = ['hero_id', 'aspect_encoded', 'villain_id', 'difficulty_encoded',
                     'avg_cost', 'event_ratio', 'ally_ratio', 'upgrade_ratio', 'support_ratio']
    
    # Obtener información de cartas de la BD para calcular costes y tipos
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Cache de información de cartas
    card_info_cache = {}
    
    for idx, row in df.iterrows():
        # Features básicas
        basic_features = [
            row['hero_id'],
            row['aspect_encoded'],
            row['villain_id'],
            row['difficulty_encoded']
        ]
        
        # Features agregadas de cartas (características generales, NO cartas específicas)
        avg_cost = 0.0
        event_count = 0
        ally_count = 0
        upgrade_count = 0
        support_count = 0
        total_cards = 0
        
        try:
            deck_cards = json.loads(row['cards']) if row['cards'] else []
            
            for card in deck_cards:
                card_id = card.get('card_id')
                quantity = card.get('quantity', 1)
                total_cards += quantity
                
                if card_id:
                    # Obtener información de la carta (con cache)
                    if card_id not in card_info_cache:
                        cursor.execute('SELECT cost, type FROM cards WHERE id = ?', (card_id,))
                        card_info = cursor.fetchone()
                        if card_info:
                            card_info_cache[card_id] = {
                                'cost': card_info[0] or 0,
                                'type': card_info[1] or ''
                            }
                        else:
                            card_info_cache[card_id] = {'cost': 0, 'type': ''}
                    
                    card_info = card_info_cache[card_id]
                    cost = card_info['cost'] or 0
                    card_type = (card_info['type'] or '').lower()
                    
                    # Acumular coste
                    avg_cost += cost * quantity
                    
                    # Contar tipos
                    if 'event' in card_type:
                        event_count += quantity
                    elif 'ally' in card_type:
                        ally_count += quantity
                    elif 'upgrade' in card_type or 'attachment' in card_type:
                        upgrade_count += quantity
                    elif 'support' in card_type:
                        support_count += quantity
        
        except (json.JSONDecodeError, KeyError):
            pass
        
        # Calcular ratios
        if total_cards > 0:
            avg_cost = avg_cost / total_cards
            event_ratio = event_count / total_cards
            ally_ratio = ally_count / total_cards
            upgrade_ratio = upgrade_count / total_cards
            support_ratio = support_count / total_cards
        else:
            avg_cost = 0.0
            event_ratio = 0.0
            ally_ratio = 0.0
            upgrade_ratio = 0.0
            support_ratio = 0.0
        
        # Combinar todas las features (SOLO características generales)
        all_features = basic_features + [
            avg_cost,
            event_ratio,
            ally_ratio,
            upgrade_ratio,
            support_ratio
        ]
        
        features_list.append(all_features)
    
    conn.close()
    
    X = np.array(features_list)
    y = df['result_encoded'].values
    
    return X, y, feature_names

def get_training_data(db_path: str = None, top_cards: list = None) -> Tuple[np.ndarray, np.ndarray, list]:
    """
    Función principal para obtener datos de entrenamiento
    
    NOTA: top_cards ya no se usa (se mantiene el parámetro por compatibilidad pero se ignora)
    
    Returns:
        X: features (solo características generales, NO cartas específicas)
        y: target (result_encoded: 0=loss, 1=win)
        feature_names: Lista de nombres de features (para debugging)
    """
    df = get_game_data_from_db(db_path)
    
    if len(df) == 0:
        raise ValueError("No hay datos de partidas en la base de datos")
    
    # top_cards ya no se usa - el modelo solo aprende características generales
    X, y, feature_names = prepare_features(df, top_cards=None)
    
    return X, y, feature_names

