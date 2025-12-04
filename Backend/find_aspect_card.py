#!/usr/bin/env python3
"""Buscar una carta de aspecto real desde MarvelCDB"""

import requests
import json

print("🔍 Buscando cartas de aspecto desde MarvelCDB...\n")

# Obtener todas las cartas
try:
    response = requests.get("https://marvelcdb.com/api/public/cards/", timeout=15)
    response.raise_for_status()
    all_cards = response.json()
    
    print(f"✅ Obtenidas {len(all_cards)} cartas\n")
    
    # Buscar cartas de aspecto (aggression, justice, leadership, protection)
    aspect_cards = []
    for card in all_cards:
        faction = card.get('faction_code', '').lower()
        type_code = card.get('type_code', '').lower()
        
        # Buscar cartas de aspecto (no héroes, no básicas, no encounter)
        if faction in ['aggression', 'justice', 'leadership', 'protection', 'pool'] and type_code != 'hero':
            aspect_cards.append(card)
            if len(aspect_cards) >= 5:  # Solo las primeras 5
                break
    
    if aspect_cards:
        print(f"📋 Encontradas {len(aspect_cards)} cartas de aspecto:\n")
        for card in aspect_cards:
            code = card.get('code')
            name = card.get('name')
            faction = card.get('faction_code')
            type_code = card.get('type_code')
            
            print(f"   Código: {code}")
            print(f"   Nombre: {name}")
            print(f"   Faction Code: {faction}")
            print(f"   Type Code: {type_code}")
            
            # Obtener la carta completa
            print(f"\n   📡 Obteniendo carta completa {code}...")
            try:
                card_response = requests.get(f"https://marvelcdb.com/api/public/card/{code}", timeout=10)
                if card_response.status_code == 200:
                    full_card = card_response.json()
                    print(f"   ✅ Campos importantes:")
                    print(f"      - code: {full_card.get('code')}")
                    print(f"      - name: {full_card.get('name')}")
                    print(f"      - type_code: {full_card.get('type_code')}")
                    print(f"      - faction_code: {full_card.get('faction_code')}")
                    print(f"      - pack_code: {full_card.get('pack_code')}")
                    print(f"      - pack_name: {full_card.get('pack_name')}")
                    
                    # Simular mapeo
                    faction_code = str(full_card.get('faction_code', '')).lower()
                    type_code_val = str(full_card.get('type_code', '')).lower()
                    
                    if type_code_val == 'hero':
                        aspect = 'hero'
                    elif faction_code in ['aggression', 'justice', 'leadership', 'protection', 'pool', 'basic', 'hero', 'encounter', 'campaign']:
                        aspect = faction_code
                    else:
                        aspect = 'basic'
                    
                    print(f"\n   🔄 Mapeo que haríamos:")
                    print(f"      - aspect (clase): {aspect}")
                    print(f"      - type: {type_code_val}")
                    print(f"      - faction_code: {faction_code}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            print("\n" + "-" * 60 + "\n")
    else:
        print("❌ No se encontraron cartas de aspecto")
        
except Exception as e:
    print(f"❌ Error: {e}")

