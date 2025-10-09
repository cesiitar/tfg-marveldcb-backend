#!/usr/bin/env python3
"""
Script de prueba para verificar que Auth0 está funcionando correctamente
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_public_endpoints():
    """Probar endpoints públicos"""
    print("🔍 Probando endpoints públicos...")
    
    endpoints = [
        "/",
        "/api/sets",
        "/api/cards",
        "/api/decks"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            print(f"✅ {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: Error - {e}")

def test_protected_endpoints():
    """Probar endpoints protegidos (deberían fallar sin token)"""
    print("\n🔒 Probando endpoints protegidos (sin token)...")
    
    endpoints = [
        "/api/user/profile",
        "/api/user/decks"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            if response.status_code == 401:
                print(f"✅ {endpoint}: 401 Unauthorized (correcto)")
            else:
                print(f"⚠️ {endpoint}: {response.status_code} (esperado 401)")
        except Exception as e:
            print(f"❌ {endpoint}: Error - {e}")

def test_docs():
    """Probar documentación de la API"""
    print("\n📚 Probando documentación...")
    
    try:
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code == 200:
            print("✅ /docs: Documentación disponible")
        else:
            print(f"⚠️ /docs: {response.status_code}")
    except Exception as e:
        print(f"❌ /docs: Error - {e}")

if __name__ == "__main__":
    print("🚀 PRUEBAS DE AUTH0 INTEGRATION")
    print("=" * 50)
    
    test_public_endpoints()
    test_protected_endpoints()
    test_docs()
    
    print("\n" + "=" * 50)
    print("✅ Pruebas completadas")
    print("\n💡 Para probar endpoints protegidos:")
    print("   1. Inicia sesión en el frontend")
    print("   2. Copia el token JWT")
    print("   3. Usa: curl -H 'Authorization: Bearer TOKEN' http://localhost:8000/api/user/profile")
