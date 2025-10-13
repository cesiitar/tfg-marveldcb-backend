#!/usr/bin/env python3
"""
Verificación rápida de usuarios en la base de datos
"""

import sqlite3
from datetime import datetime

def get_db_connection():
    """Obtener conexión a la base de datos"""
    conn = sqlite3.connect('marvel_cards.db')
    conn.row_factory = sqlite3.Row
    return conn

def quick_check():
    """Verificación rápida de usuarios"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Contar usuarios
    cursor.execute("SELECT COUNT(*) as count FROM users")
    count = cursor.fetchone()['count']
    
    print(f"👥 USUARIOS EN BD: {count}")
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 40)
    
    if count > 0:
        # Mostrar últimos 3 usuarios
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT 3")
        users = cursor.fetchall()
        
        for user in users:
            print(f"📧 {user['email']}")
            print(f"🔑 {user['auth0_id'][:30]}...")
            print(f"📅 {user['created_at']}")
            print()
    
    conn.close()

if __name__ == "__main__":
    quick_check()

