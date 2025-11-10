"""
Script para eliminar los datos de prueba (mazos y partidas) generados para entrenar la IA.
"""

import sqlite3

def get_db_connection():
    """Obtener conexión a la base de datos"""
    conn = sqlite3.connect('marvel_cards.db')
    conn.row_factory = sqlite3.Row
    return conn

def delete_test_data():
    """Eliminar todos los datos de prueba"""
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
        return
    
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
        return
    
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
    print()
    print("🎉 ¡Datos de prueba eliminados exitosamente!")

if __name__ == '__main__':
    delete_test_data()

