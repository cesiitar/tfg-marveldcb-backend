#!/usr/bin/env python3
"""Script para depurar el mapeo de cartas desde MarvelCDB"""

import requests
import json
import sqlite3

# Probar con diferentes tipos de cartas
test_codes = {
    "hero": "01001",  # Probablemente un héroe
    "aspect": "01002",  # Probablemente una carta de aspecto
    "basic": "01003"  # Probablemente una carta básica
}

print("🔍 Depurando mapeo de cartas desde MarvelCDB\n")
print("=" * 60)

for card_type, code in test_codes.items():
    print(f"\n📋 Probando carta tipo {card_type} (código: {code})")
    print("-" * 60)
    
    try:
        response = requests.get(f"https://marvelcdb.com/api/public/card/{code}", timeout=10)
        
        if response.status_code == 200:
            card = response.json()
            
            print(f"✅ Carta encontrada: {card.get('name')}")
            print(f"\n📊 Campos importantes:")
            print(f"   - code: {card.get('code')}")
            print(f"   - name: {card.get('name')}")
            print(f"   - type_code: {card.get('type_code')}")
            print(f"   - type_name: {card.get('type_name')}")
            print(f"   - faction_code: {card.get('faction_code')}")
            print(f"   - faction_name: {card.get('faction_name')}")
            print(f"   - pack_code: {card.get('pack_code')}")
            print(f"   - pack_name: {card.get('pack_name')}")
            print(f"   - card_set_name: {card.get('card_set_name')}")
            
            # Simular el mapeo que hacemos
            code_val = card.get('code', '')
            if code_val and str(code_val).isdigit():
                card_id = int(code_val)
            else:
                card_id = abs(hash(str(code_val))) % 1000000
            
            faction_code = str(card.get('faction_code', '')).lower()
            type_code = str(card.get('type_code', '')).lower()
            
            # Mapeo de aspect
            if type_code == 'hero':
                aspect = 'hero'
            elif faction_code in ['aggression', 'justice', 'leadership', 'protection', 'pool', 'basic', 'hero', 'encounter', 'campaign']:
                aspect = faction_code
            else:
                aspect = 'basic'
            
            print(f"\n🔄 Mapeo resultante:")
            print(f"   - id: {card_id}")
            print(f"   - aspect (clase): {aspect}")
            print(f"   - type: {type_code}")
            print(f"   - faction_code original: {faction_code}")
            
            # Verificar si está en BD
            conn = sqlite3.connect('marvel_cards.db')
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, aspect, type, faction_code FROM cards WHERE id = ?', (card_id,))
            db_card = cursor.fetchone()
            conn.close()
            
            if db_card:
                print(f"\n💾 En nuestra BD:")
                print(f"   - id: {db_card[0]}")
                print(f"   - name: {db_card[1]}")
                print(f"   - aspect: {db_card[2]}")
                print(f"   - type: {db_card[3]}")
                print(f"   - faction_code: {db_card[4]}")
                
                if str(db_card[2]) != aspect:
                    print(f"\n   ⚠️  PROBLEMA: El aspect no coincide!")
                    print(f"      Esperado: {aspect}")
                    print(f"      En BD: {db_card[2]}")
                if str(db_card[3]) != type_code:
                    print(f"\n   ⚠️  PROBLEMA: El type no coincide!")
                    print(f"      Esperado: {type_code}")
                    print(f"      En BD: {db_card[3]}")
            else:
                print(f"\n   ℹ️  Esta carta NO está en la BD")
                
        else:
            print(f"❌ Error: Status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("\n🔍 Buscando un héroe real en la BD para comparar...")

conn = sqlite3.connect('marvel_cards.db')
cursor = conn.cursor()
cursor.execute('SELECT id, name, aspect, type, faction_code FROM cards WHERE type = "hero" LIMIT 3')
heroes = cursor.fetchall()
conn.close()

if heroes:
    print("\n🦸 Héroes en nuestra BD:")
    for hero in heroes:
        print(f"   - ID: {hero[0]}, Name: {hero[1]}, Aspect: {hero[2]}, Type: {hero[3]}, Faction: {hero[4]}")

