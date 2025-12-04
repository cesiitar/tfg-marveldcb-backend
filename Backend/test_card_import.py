#!/usr/bin/env python3
"""Script para probar la importación de una carta desde MarvelCDB"""

import requests
import json
import sqlite3

# Conectar a la BD
conn = sqlite3.connect('marvel_cards.db')
cursor = conn.cursor()

# Obtener algunas cartas desde la API para ver qué códigos hay
print("📡 Obteniendo lista de cartas desde MarvelCDB...")
try:
    response = requests.get("https://marvelcdb.com/api/public/cards/", timeout=15)
    response.raise_for_status()
    all_cards = response.json()
    print(f"✅ Obtenidas {len(all_cards)} cartas desde MarvelCDB\n")
    
    # Buscar una carta que NO esté en nuestra BD
    print("🔍 Buscando una carta que NO esté en nuestra BD...\n")
    
    for card in all_cards[:50]:  # Revisar las primeras 50
        code = card.get('code', '')
        if not code:
            continue
        
        # Verificar si existe en BD
        try:
            card_id = int(code) if code.isdigit() else abs(hash(code)) % 1000000
        except:
            card_id = abs(hash(code)) % 1000000
        
        cursor.execute('SELECT COUNT(*) FROM cards WHERE id = ?', (card_id,))
        exists = cursor.fetchone()[0] > 0
        
        if not exists:
            print(f"✅ Carta {code} NO está en la BD - perfecta para probar")
            print(f"   Nombre: {card.get('name')}")
            print(f"   Tipo: {card.get('type_code')}")
            print(f"   Pack: {card.get('pack_name')}")
            
            # Obtener la carta completa
            print(f"\n📡 Obteniendo carta completa {code} desde MarvelCDB...")
            try:
                card_response = requests.get(f"https://marvelcdb.com/api/public/card/{code}", timeout=10)
                card_response.raise_for_status()
                full_card = card_response.json()
                
                print(f"\n📋 Campos devueltos por la API para carta {code}:")
                print(f"   Total de campos: {len(full_card)}")
                print(f"\n   Todos los campos:")
                for key, value in full_card.items():
                    if value is None:
                        value_str = "None"
                    elif isinstance(value, (list, dict)):
                        value_str = str(value)[:60]
                    else:
                        value_str = str(value)[:60]
                    print(f"   - {key}: {value_str}")
                
                print(f"\n✅ Esta carta se puede usar para probar el endpoint de importación")
                print(f"   Código: {code}")
                print(f"   Nombre: {full_card.get('name')}")
                break
                
            except Exception as e:
                print(f"❌ Error obteniendo carta completa {code}: {e}")
                continue
    
    if not any(True for _ in [None]):  # Si no encontramos ninguna
        print("⚠️  No se encontró una carta que no esté en la BD en las primeras 50")
        print("   Probando con una carta aleatoria más adelante...")
        
        # Probar con una carta más adelante en la lista
        if len(all_cards) > 100:
            test_card = all_cards[100]
            code = test_card.get('code', '')
            print(f"\n📡 Probando con carta {code}...")
            try:
                card_response = requests.get(f"https://marvelcdb.com/api/public/card/{code}", timeout=10)
                card_response.raise_for_status()
                full_card = card_response.json()
                
                print(f"\n📋 Campos devueltos por la API para carta {code}:")
                print(f"   Total de campos: {len(full_card)}")
                print(f"\n   Campos principales:")
                for key in ['code', 'name', 'type_code', 'faction_code', 'pack_code', 'pack_name', 
                           'cost', 'deck_limit', 'health', 'attack', 'threat', 'traits', 'text', 'is_unique', 'quantity']:
                    value = full_card.get(key)
                    if value is not None:
                        value_str = str(value)[:60] if not isinstance(value, (list, dict)) else str(value)[:60]
                        print(f"   - {key}: {value_str}")
                
                print(f"\n✅ Esta carta se puede usar para probar")
                print(f"   Código: {code}")
                print(f"   Nombre: {full_card.get('name')}")
            except Exception as e:
                print(f"❌ Error: {e}")
                
except Exception as e:
    print(f"❌ Error obteniendo cartas: {e}")

conn.close()
