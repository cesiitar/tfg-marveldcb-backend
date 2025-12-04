#!/usr/bin/env python3
"""Script para probar una carta específica desde MarvelCDB"""

import requests
import json
import sqlite3

# Probar con una carta de un set más reciente (ej: código 90001+)
test_code = "90001"  # Probablemente de un set más reciente

print(f"📡 Obteniendo carta {test_code} desde MarvelCDB...")
try:
    response = requests.get(f"https://marvelcdb.com/api/public/card/{test_code}", timeout=10)
    
    if response.status_code == 200:
        card = response.json()
        
        print(f"\n✅ Carta encontrada: {card.get('name')}")
        print(f"\n📋 Todos los campos devueltos por la API:")
        print(f"   Total de campos: {len(card)}")
        print()
        
        for key, value in card.items():
            if value is None:
                value_str = "None"
            elif isinstance(value, (list, dict)):
                value_str = json.dumps(value)[:80]
            else:
                value_str = str(value)[:80]
            print(f"   - {key}: {value_str}")
        
        # Verificar si está en BD
        conn = sqlite3.connect('marvel_cards.db')
        cursor = conn.cursor()
        try:
            card_id = int(test_code) if test_code.isdigit() else abs(hash(test_code)) % 1000000
        except:
            card_id = abs(hash(test_code)) % 1000000
        
        cursor.execute('SELECT COUNT(*) FROM cards WHERE id = ?', (card_id,))
        exists = cursor.fetchone()[0] > 0
        conn.close()
        
        if exists:
            print(f"\n⚠️  Esta carta YA está en la BD")
        else:
            print(f"\n✅ Esta carta NO está en la BD - perfecta para probar importación")
            print(f"\n   Puedes probar el endpoint con:")
            print(f"   POST /api/cards/import-missing")
            print(f"   Body: {{ \"card_codes\": [\"{test_code}\"] }}")
    else:
        print(f"❌ Error: Status {response.status_code}")
        print(f"   Probando con otro código...")
        
        # Probar con otro código
        for code in ["01001", "01002", "02001", "03001"]:
            print(f"\n📡 Probando con código {code}...")
            try:
                r = requests.get(f"https://marvelcdb.com/api/public/card/{code}", timeout=5)
                if r.status_code == 200:
                    c = r.json()
                    print(f"✅ Funciona! Carta: {c.get('name')}")
                    print(f"   Código: {code}")
                    break
            except:
                continue
        
except Exception as e:
    print(f"❌ Error: {e}")

