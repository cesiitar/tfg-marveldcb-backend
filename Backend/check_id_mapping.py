#!/usr/bin/env python3
"""Verificar si el mapeo de IDs está causando problemas"""

import sqlite3
import requests

# Códigos de ejemplo de MarvelCDB
test_codes = ["01001", "01002", "01050", "01051"]

print("🔍 Verificando mapeo de IDs\n")
print("=" * 60)

conn = sqlite3.connect('marvel_cards.db')
cursor = conn.cursor()

for code in test_codes:
    print(f"\n📋 Código MarvelCDB: {code}")
    
    # Cómo lo convertimos nosotros
    if code.isdigit():
        our_id = int(code)
    else:
        our_id = abs(hash(code)) % 1000000
    
    print(f"   Nuestro ID calculado: {our_id}")
    
    # Buscar en BD
    cursor.execute('SELECT id, name, aspect, type, faction_code FROM cards WHERE id = ?', (our_id,))
    db_card = cursor.fetchone()
    
    if db_card:
        print(f"   ✅ Encontrado en BD:")
        print(f"      - ID: {db_card[0]}")
        print(f"      - Name: {db_card[1]}")
        print(f"      - Aspect: {db_card[2]}")
        print(f"      - Type: {db_card[3]}")
        print(f"      - Faction: {db_card[4]}")
        
        # Obtener desde MarvelCDB para comparar
        try:
            response = requests.get(f"https://marvelcdb.com/api/public/card/{code}", timeout=5)
            if response.status_code == 200:
                marvelcdb_card = response.json()
                print(f"\n   📡 Desde MarvelCDB:")
                print(f"      - Code: {marvelcdb_card.get('code')}")
                print(f"      - Name: {marvelcdb_card.get('name')}")
                print(f"      - Type Code: {marvelcdb_card.get('type_code')}")
                print(f"      - Faction Code: {marvelcdb_card.get('faction_code')}")
                
                # Verificar mapeo
                faction_code = str(marvelcdb_card.get('faction_code', '')).lower()
                type_code = str(marvelcdb_card.get('type_code', '')).lower()
                
                if type_code == 'hero':
                    expected_aspect = 'hero'
                elif faction_code in ['aggression', 'justice', 'leadership', 'protection', 'pool', 'basic', 'hero', 'encounter', 'campaign']:
                    expected_aspect = faction_code
                else:
                    expected_aspect = 'basic'
                
                print(f"\n   🔄 Aspect esperado: {expected_aspect}")
                print(f"   💾 Aspect en BD: {db_card[2]}")
                
                if str(db_card[2]) != expected_aspect:
                    print(f"   ⚠️  PROBLEMA: Aspect no coincide!")
                if str(db_card[3]) != type_code:
                    print(f"   ⚠️  PROBLEMA: Type no coincide!")
        except:
            pass
    else:
        print(f"   ❌ NO encontrado en BD con ID {our_id}")
        
        # Buscar por nombre
        try:
            response = requests.get(f"https://marvelcdb.com/api/public/card/{code}", timeout=5)
            if response.status_code == 200:
                marvelcdb_card = response.json()
                name = marvelcdb_card.get('name')
                cursor.execute('SELECT id, name, aspect, type FROM cards WHERE name = ?', (name,))
                by_name = cursor.fetchall()
                if by_name:
                    print(f"   ℹ️  Pero existe por nombre:")
                    for card in by_name:
                        print(f"      - ID: {card[0]}, Name: {card[1]}, Aspect: {card[2]}, Type: {card[3]}")
        except:
            pass

conn.close()

