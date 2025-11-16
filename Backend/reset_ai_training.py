"""
Script para eliminar completamente el entrenamiento de IA y empezar de 0:
- Elimina el modelo SVM entrenado
- Elimina todos los mazos y partidas de prueba
- Elimina el usuario de prueba
"""

import sqlite3
import os

def get_db_connection():
    """Obtener conexión a la base de datos"""
    conn = sqlite3.connect('marvel_cards.db')
    conn.row_factory = sqlite3.Row
    return conn

def delete_model():
    """Eliminar el modelo SVM entrenado"""
    model_path = os.path.join('ml', 'saved_models', 'villain_svm_model.pkl')
    
    if os.path.exists(model_path):
        os.remove(model_path)
        print(f"✅ Modelo SVM eliminado: {model_path}")
        return True
    else:
        print(f"ℹ️  No se encontró modelo SVM en: {model_path}")
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


