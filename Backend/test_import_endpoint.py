#!/usr/bin/env python3
"""Script para probar el endpoint de importación"""

import requests
import json

# URL del backend (ajustar si es necesario)
BASE_URL = "http://localhost:8000"

# Código de carta que NO está en la BD
test_code = "90001"

print(f"🧪 Probando importación de carta {test_code}...\n")

# 1. Verificar que no está en la BD
print("1️⃣ Verificando si la carta está en la BD...")
try:
    response = requests.post(
        f"{BASE_URL}/api/cards/check-missing",
        json={"card_codes": [test_code]},
        timeout=5
    )
    if response.status_code == 200:
        result = response.json()
        print(f"   Resultado: {json.dumps(result, indent=2)}")
        if test_code in result.get('missing', []):
            print(f"   ✅ Confirmado: La carta {test_code} NO está en la BD")
        else:
            print(f"   ⚠️  La carta {test_code} ya está en la BD")
    else:
        print(f"   ❌ Error: {response.status_code}")
        print(f"   {response.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    print(f"   (¿Está el servidor corriendo en {BASE_URL}?)")

print("\n2️⃣ Importando la carta...")
try:
    response = requests.post(
        f"{BASE_URL}/api/cards/import-missing",
        json={"card_codes": [test_code]},
        timeout=30
    )
    if response.status_code == 200:
        result = response.json()
        print(f"   Resultado: {json.dumps(result, indent=2)}")
        
        if result.get('imported', 0) > 0:
            print(f"   ✅ ¡Carta importada exitosamente!")
        elif result.get('skipped', 0) > 0:
            print(f"   ⏭️  Carta ya existía (se omitió)")
        elif result.get('failed', 0) > 0:
            print(f"   ❌ Error al importar")
            if 'errors' in result:
                for error in result['errors']:
                    print(f"      - {error.get('code')}: {error.get('error')}")
    else:
        print(f"   ❌ Error: {response.status_code}")
        print(f"   {response.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    print(f"   (¿Está el servidor corriendo en {BASE_URL}?)")

print("\n3️⃣ Verificando nuevamente...")
try:
    response = requests.post(
        f"{BASE_URL}/api/cards/check-missing",
        json={"card_codes": [test_code]},
        timeout=5
    )
    if response.status_code == 200:
        result = response.json()
        if test_code in result.get('existing', []):
            print(f"   ✅ La carta {test_code} ahora SÍ está en la BD")
        else:
            print(f"   ⚠️  La carta {test_code} aún no está en la BD")
except Exception as e:
    print(f"   ❌ Error: {e}")

