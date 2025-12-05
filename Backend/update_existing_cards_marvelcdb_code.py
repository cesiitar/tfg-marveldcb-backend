#!/usr/bin/env python3
"""
Script para actualizar todas las cartas existentes con su marvelcdb_code.

Este script:
1. Obtiene todas las cartas de MarvelCDB
2. Para cada carta, busca en nuestra BD por id (que se calcula igual que antes)
3. Actualiza el campo marvelcdb_code con el code original de MarvelCDB
"""

import sqlite3
import requests
import time

MARVELCDB_API_BASE = "https://marvelcdb.com/api/public"

def get_db_connection():
    import os
    # Buscar la base de datos en el directorio actual o en Backend/
    db_path = 'marvel_cards.db'
    if not os.path.exists(db_path):
        db_path = os.path.join('Backend', 'marvel_cards.db')
    if not os.path.exists(db_path):
        db_path = os.path.join(os.path.dirname(__file__), 'marvel_cards.db')
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def convert_code_to_id(code):
    """Convierte el code de MarvelCDB a id (igual que en init_all.py)"""
    if code and str(code).isdigit():
        return int(code)
    else:
        return abs(hash(str(code))) % 1000000

def update_marvelcdb_codes():
    """Actualiza todas las cartas existentes con su marvelcdb_code"""
    print("🔄 Actualizando cartas existentes con marvelcdb_code...")
    print("=" * 60)
    
    # Asegurar que la columna existe
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar si la columna existe
    cursor.execute("PRAGMA table_info(cards)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'marvelcdb_code' not in columns:
        print("📋 Añadiendo columna marvelcdb_code...")
        cursor.execute('ALTER TABLE cards ADD COLUMN marvelcdb_code VARCHAR(20)')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_marvelcdb_code ON cards(marvelcdb_code)')
        conn.commit()
        print("✅ Columna añadida")
    
    # Obtener todas las cartas de MarvelCDB
    print("\n📡 Obteniendo todas las cartas de MarvelCDB...")
    try:
        response = requests.get(f"{MARVELCDB_API_BASE}/cards/", timeout=30)
        response.raise_for_status()
        all_cards = response.json()
        print(f"✅ Obtenidas {len(all_cards)} cartas de MarvelCDB")
    except Exception as e:
        print(f"❌ Error obteniendo cartas de MarvelCDB: {e}")
        conn.close()
        return
    
    # Contadores
    updated = 0
    not_found = 0
    already_has_code = 0
    errors = 0
    
    print(f"\n🔄 Procesando cartas...")
    print("-" * 60)
    
    for i, marvelcdb_card in enumerate(all_cards):
        if (i + 1) % 100 == 0:
            print(f"   Procesadas {i + 1}/{len(all_cards)} cartas...")
        
        try:
            code = str(marvelcdb_card.get('code', ''))
            if not code:
                continue
            
            # Convertir code a id (igual que en init_all.py)
            card_id = convert_code_to_id(code)
            
            # Buscar la carta en nuestra BD por id
            cursor.execute('SELECT id, name, marvelcdb_code FROM cards WHERE id = ?', (card_id,))
            db_card = cursor.fetchone()
            
            if not db_card:
                # La carta no existe en nuestra BD, continuar
                not_found += 1
                continue
            
            # Verificar si ya tiene marvelcdb_code
            if db_card['marvelcdb_code']:
                already_has_code += 1
                continue
            
            # Actualizar el marvelcdb_code
            cursor.execute('UPDATE cards SET marvelcdb_code = ? WHERE id = ?', (code, card_id))
            updated += 1
            
            # Commit cada 50 cartas para no saturar
            if updated % 50 == 0:
                conn.commit()
        
        except Exception as e:
            errors += 1
            print(f"   ⚠️  Error procesando carta {code}: {e}")
            continue
    
    # Commit final
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ Actualización completada:")
    print(f"   - Cartas actualizadas: {updated}")
    print(f"   - Ya tenían code: {already_has_code}")
    print(f"   - No encontradas en BD: {not_found}")
    print(f"   - Errores: {errors}")
    print(f"   - Total procesadas: {len(all_cards)}")

if __name__ == "__main__":
    update_marvelcdb_codes()

