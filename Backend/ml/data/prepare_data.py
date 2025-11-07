import sqlite3
import pandas as pd
import json
from typing import Tuple
import numpy as np
import os

def get_db_path():
    """Obtiene la ruta a la base de datos"""
    # Obtener el directorio del script actual
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Subir dos niveles: ml/data -> Backend
    backend_dir = os.path.dirname(os.path.dirname(current_dir))
    db_path = os.path.join(backend_dir, 'marvel_cards.db')
    return db_path

def get_game_data_from_db(db_path: str = None) -> pd.DataFrame:
    """
    Extrae datos de partidas de la base de datos
    
    Returns:
        DataFrame con: deck_id, hero_id, aspect, villain_id, difficulty, result
    """
    if db_path is None:
        db_path = get_db_path()
    
    conn = sqlite3.connect(db_path)
    
    query = """
    SELECT 
        gc.id as game_id,
        gc.deck_id,
        gc.villain_id,
        gc.difficulty,
        gc.result,
        d.hero_id,
        d.aspect
    FROM game_configurations gc
    JOIN decks d ON gc.deck_id = d.id
    WHERE gc.result IS NOT NULL
        AND d.hero_id IS NOT NULL
        AND d.aspect IS NOT NULL
        AND gc.villain_id IS NOT NULL
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return df

def prepare_features(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """
    Prepara features para el modelo SVM
    
    Features:
    - hero_id (numérico)
    - aspect_encoded (aggression=0, justice=1, leadership=2, protection=3)
    - villain_id (numérico)
    - difficulty_encoded (normal=0, expert=1)
    
    Target:
    - result_encoded (loss=0, win=1)
    
    Returns:
        X: array de features (n_samples, 4)
        y: array de resultados (n_samples,)
    """
    # Codificar aspect
    aspect_map = {
        'aggression': 0,
        'justice': 1,
        'leadership': 2,
        'protection': 3
    }
    df['aspect_encoded'] = df['aspect'].map(aspect_map).fillna(0)
    
    # Codificar difficulty
    df['difficulty_encoded'] = df['difficulty'].map({'normal': 0, 'expert': 1}).fillna(0)
    
    # Codificar result (win=1, loss=0)
    df['result_encoded'] = df['result'].map({'win': 1, 'loss': 0}).fillna(0)
    
    # Seleccionar features
    X = df[['hero_id', 'aspect_encoded', 'villain_id', 'difficulty_encoded']].values
    y = df['result_encoded'].values
    
    return X, y

def get_training_data(db_path: str = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Función principal para obtener datos de entrenamiento
    
    Returns:
        X: features (hero_id, aspect_encoded, villain_id, difficulty_encoded)
        y: target (result_encoded: 0=loss, 1=win)
    """
    df = get_game_data_from_db(db_path)
    
    if len(df) == 0:
        raise ValueError("No hay datos de partidas en la base de datos")
    
    X, y = prepare_features(df)
    
    return X, y

