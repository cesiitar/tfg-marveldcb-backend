#!/usr/bin/env python3
"""
Script para crear la tabla users y añadir user_id a decks
"""

import sqlite3

def setup_database():
    """Configurar la base de datos con tabla users y user_id en decks"""
    
    conn = sqlite3.connect('marvel_cards.db')
    cursor = conn.cursor()
    
    print("🔧 CONFIGURANDO BASE DE DATOS")
    print("=" * 50)
    
    # 1. Crear tabla users
    print("\n1. 👤 Creando tabla 'users'...")
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                auth0_id VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255) NOT NULL,
                name VARCHAR(255),
                picture_url VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("   ✅ Tabla 'users' creada")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 2. Añadir columna user_id a tabla decks
    print("\n2. 🎯 Añadiendo columna 'user_id' a tabla 'decks'...")
    try:
        # Verificar si ya existe la columna
        cursor.execute("PRAGMA table_info(decks)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_id' not in columns:
            cursor.execute('ALTER TABLE decks ADD COLUMN user_id TEXT')
            print("   ✅ Columna 'user_id' añadida")
        else:
            print("   ✅ Columna 'user_id' ya existe")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 3. Verificar estructura final
    print("\n3. 📋 Verificando estructura final...")
    
    # Tabla users
    cursor.execute("PRAGMA table_info(users)")
    users_columns = cursor.fetchall()
    print("   Tabla 'users':")
    for col in users_columns:
        print(f"     {col[1]} ({col[2]})")
    
    # Tabla decks
    cursor.execute("PRAGMA table_info(decks)")
    decks_columns = cursor.fetchall()
    print("   Tabla 'decks':")
    for col in decks_columns:
        print(f"     {col[1]} ({col[2]})")
    
    # 4. Contar registros
    print("\n4. 📊 Conteo de registros:")
    cursor.execute("SELECT COUNT(*) FROM cards")
    cards_count = cursor.fetchone()[0]
    print(f"   Cards: {cards_count}")
    
    cursor.execute("SELECT COUNT(*) FROM decks")
    decks_count = cursor.fetchone()[0]
    print(f"   Decks: {decks_count}")
    
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    print(f"   Users: {users_count}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Base de datos configurada correctamente")

if __name__ == "__main__":
    setup_database()



