#!/usr/bin/env python3
"""Verificar qué cartas no se encontraron y por qué"""

import sqlite3
import requests

MARVELCDB_API_BASE = "https://marvelcdb.com/api/public"

def get_db_connection():
    import os
    db_path = 'marvel_cards.db'
    if not os.path.exists(db_path):
        db_path = os.path.join('Backend', 'marvel_cards.db')
    if not os.path.exists(db_path):
        db_path = os.path.join(os.path.dirname(__file__), 'marvel_cards.db')
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def convert_code_to_id(code):
    """Convierte el code de MarvelCDB a id"""
    if code and str(code).isdigit():
        return int(code)
    else:
        return abs(hash(str(code))) % 1000000

def check_missing():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("🔍 Verificando cartas no encontradas...\n")
    
    # Obtener todas las cartas de MarvelCDB
    response = requests.get(f"{MARVELCDB_API_BASE}/cards/", timeout=30)
    all_cards = response.json()
    
    not_found = []
    found_by_id = []
    found_by_name = []
    
    for card in all_cards[:50]:  # Solo las primeras 50 para no saturar
        code = str(card.get('code', ''))
        if not code:
            continue
        
        card_id = convert_code_to_id(code)
        name = card.get('name', '')
        type_code = card.get('type_code', '')
        faction_code = card.get('faction_code', '')
        
        # Buscar por id
        cursor.execute('SELECT id, name, type, aspect FROM cards WHERE id = ?', (card_id,))
        by_id = cursor.fetchone()
        
        if by_id:
            found_by_id.append({
                'code': code,
                'name': name,
                'id': card_id,
                'found_name': by_id['name']
            })
        else:
            # Buscar por nombre
            cursor.execute('SELECT id, name, type, aspect FROM cards WHERE name = ?', (name,))
            by_name = cursor.fetchone()
            
            if by_name:
                found_by_name.append({
                    'code': code,
                    'name': name,
                    'expected_id': card_id,
                    'found_id': by_name['id'],
                    'found_name': by_name['name']
                })
            else:
                not_found.append({
                    'code': code,
                    'name': name,
                    'type': type_code,
                    'faction': faction_code,
                    'expected_id': card_id
                })
    
    conn.close()
    
    print(f"📊 Resultados (primeras 50 cartas):")
    print(f"   - Encontradas por ID: {len(found_by_id)}")
    print(f"   - Encontradas por nombre (ID diferente): {len(found_by_name)}")
    print(f"   - No encontradas: {len(not_found)}\n")
    
    if found_by_name:
        print("⚠️  Cartas encontradas por nombre pero con ID diferente:")
        for card in found_by_name[:5]:
            print(f"   - {card['name']}: Code={card['code']}, Expected ID={card['expected_id']}, Found ID={card['found_id']}")
        print()
    
    if not_found:
        print("❌ Cartas no encontradas (primeras 10):")
        for card in not_found[:10]:
            print(f"   - {card['name']} (Code: {card['code']}, Type: {card['type']}, Faction: {card['faction']})")
        print()
        
        # Verificar tipos de cartas no encontradas
        types = {}
        for card in not_found:
            t = card['type']
            types[t] = types.get(t, 0) + 1
        
        print("📋 Tipos de cartas no encontradas:")
        for t, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {t}: {count}")

if __name__ == "__main__":
    check_missing()

