"""
Script para eliminar completamente el entrenamiento de IA y empezar de 0:
- Elimina el modelo SVM entrenado
- Elimina todos los mazos y partidas de prueba
- Elimina el usuario de prueba
"""

import sqlite3
import os
import sys

# Añadir path para importar db_utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_utils import get_db_connection

def get_possible_model_paths():
    """Posibles ubicaciones del modelo, priorizando volumen persistente."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    paths = []

    env_model_path = os.getenv("MODEL_PATH")
    if env_model_path:
        paths.append(env_model_path)

    # Rutas relativas habituales
    paths.append(os.path.join(script_dir, 'ml', 'saved_models', 'model.pkl'))
    paths.append(os.path.join(script_dir, 'saved_models', 'model.pkl'))
    paths.append(os.path.join('ml', 'saved_models', 'model.pkl'))
    paths.append(os.path.join('saved_models', 'model.pkl'))

    return paths


def delete_model():
    """Eliminar el modelo SVM entrenado"""
    possible_paths = get_possible_model_paths()

    for model_path in possible_paths:
        if os.path.exists(model_path):
            os.remove(model_path)
            print(f"✅ Modelo SVM eliminado: {model_path}")
            return True
    
    print("ℹ️  No se encontró modelo SVM. Rutas buscadas:")
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        exists = "✓" if os.path.exists(path) else "✗"
        print(f"   {exists} {abs_path}")
    return False

def delete_test_data():
    """Eliminar todos los datos de prueba (mazos y partidas)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("🗑️  Eliminando datos de prueba...")
    
    # 1. Buscar el usuario de prueba
    cursor.execute('''
        SELECT id FROM users WHERE auth0_id = 'test_user_ai_training'
    ''')
    
    user_row = cursor.fetchone()
    
    if not user_row:
        print("✅ No se encontraron datos de prueba para eliminar")
        conn.close()
        return 0, 0
    
    user_id = user_row['id']
    print(f"📋 Usuario de prueba encontrado: ID={user_id}")
    
    # 2. Contar mazos y partidas antes de eliminar
    cursor.execute('SELECT COUNT(*) FROM decks WHERE user_id = ?', (user_id,))
    decks_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM game_configurations WHERE user_id = ?', (user_id,))
    games_count = cursor.fetchone()[0]
    
    print(f"📊 Datos encontrados:")
    print(f"   - Mazos: {decks_count}")
    print(f"   - Partidas: {games_count}")
    
    if decks_count == 0 and games_count == 0:
        print("✅ No hay datos de prueba para eliminar")
        conn.close()
        return 0, 0
    
    # 3. Eliminar partidas primero (por la foreign key)
    cursor.execute('DELETE FROM game_configurations WHERE user_id = ?', (user_id,))
    games_deleted = cursor.rowcount
    
    # 4. Eliminar mazos (esto también eliminará los favoritos por ON DELETE CASCADE)
    cursor.execute('DELETE FROM decks WHERE user_id = ?', (user_id,))
    decks_deleted = cursor.rowcount
    
    # 5. Eliminar el usuario de prueba
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    user_deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"✅ Datos eliminados:")
    print(f"   - Partidas eliminadas: {games_deleted}")
    print(f"   - Mazos eliminados: {decks_deleted}")
    print(f"   - Usuario eliminado: {user_deleted}")
    
    return decks_deleted, games_deleted

def delete_all_production_data():
    """Eliminar TODAS las partidas, TODOS los mazos y el modelo entrenado (para producción)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("🗑️  Eliminando TODOS los datos de producción...")
    print()
    
    # 1. Contar antes de eliminar
    cursor.execute('SELECT COUNT(*) FROM game_configurations')
    games_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM decks')
    decks_count = cursor.fetchone()[0]
    
    print(f"📊 Datos encontrados:")
    print(f"   - Partidas: {games_count}")
    print(f"   - Mazos: {decks_count}")
    print()
    
    # 2. Eliminar partidas primero (por la foreign key)
    cursor.execute('DELETE FROM game_configurations')
    games_deleted = cursor.rowcount
    
    # 3. Eliminar mazos (esto también eliminará los favoritos por ON DELETE CASCADE)
    cursor.execute('DELETE FROM decks')
    decks_deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    # 4. Eliminar modelo SVM
    model_deleted = delete_model()
    
    print()
    print("✅ Datos eliminados:")
    print(f"   - Partidas eliminadas: {games_deleted}")
    print(f"   - Mazos eliminados: {decks_deleted}")
    print(f"   - Modelo SVM: {'Eliminado' if model_deleted else 'No existía'}")
    
    return decks_deleted, games_deleted, model_deleted

def reset_ai_training():
    """Eliminar todo y empezar de 0"""
    print("🔄 Reiniciando entrenamiento de IA desde cero...")
    print()
    
    # 1. Eliminar modelo SVM
    model_deleted = delete_model()
    print()
    
    # 2. Eliminar datos de prueba
    decks_deleted, games_deleted = delete_test_data()
    print()
    
    print("🎉 ¡Reinicio completado!")
    print()
    print("📋 Resumen:")
    print(f"   - Modelo SVM: {'Eliminado' if model_deleted else 'No existía'}")
    print(f"   - Mazos eliminados: {decks_deleted}")
    print(f"   - Partidas eliminadas: {games_deleted}")
    print()
    print("💡 Ahora puedes:")
    print("   1. Generar nuevos datos de prueba con: python generate_test_data.py")
    print("   2. Entrenar la IA con: python -m ml.models.train_model")
    print("   3. O usar el endpoint: POST /api/recommendations/train")

if __name__ == '__main__':
    reset_ai_training()


