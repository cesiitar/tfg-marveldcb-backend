#!/usr/bin/env python3
"""
Monitor de usuarios en tiempo real para debugging
"""

import sqlite3
import time
import os
from datetime import datetime

def get_db_connection():
    """Obtener conexión a la base de datos"""
    conn = sqlite3.connect('marvel_cards.db')
    conn.row_factory = sqlite3.Row
    return conn

def clear_screen():
    """Limpiar pantalla"""
    os.system('cls' if os.name == 'nt' else 'clear')

def display_users():
    """Mostrar usuarios en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener todos los usuarios
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    
    print("👥 USUARIOS EN LA BASE DE DATOS")
    print("=" * 80)
    print(f"📊 Total: {len(users)} usuarios")
    print(f"⏰ Última actualización: {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 80)
    
    if not users:
        print("❌ No hay usuarios en la base de datos")
    else:
        for i, user in enumerate(users, 1):
            print(f"{i}. 👤 ID: {user['id']}")
            print(f"   📧 Email: {user['email']}")
            print(f"   🔑 Auth0 ID: {user['auth0_id']}")
            print(f"   👨‍💼 Nombre: {user['name'] or 'No especificado'}")
            print(f"   🖼️ Imagen: {user['picture_url'] or 'No especificada'}")
            print(f"   📅 Creado: {user['created_at']}")
            print(f"   🔄 Actualizado: {user['updated_at']}")
            print()
    
    conn.close()

def monitor_changes():
    """Monitorear cambios en la base de datos"""
    print("🔍 MONITOR DE USUARIOS EN TIEMPO REAL")
    print("=" * 80)
    print("💡 Presiona Ctrl+C para salir")
    print("🔄 Actualizando cada 2 segundos...")
    print()
    
    last_count = 0
    
    try:
        while True:
            # Limpiar pantalla
            clear_screen()
            
            # Mostrar usuarios
            display_users()
            
            # Verificar cambios
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM users")
            current_count = cursor.fetchone()['count']
            conn.close()
            
            if current_count != last_count:
                print(f"🆕 ¡CAMBIO DETECTADO! Usuarios: {last_count} → {current_count}")
                last_count = current_count
            
            # Esperar 2 segundos
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitor detenido por el usuario")
        print("¡Gracias por usar el monitor!")

def show_recent_activity():
    """Mostrar actividad reciente"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener usuarios creados en las últimas 24 horas
    cursor.execute("""
        SELECT * FROM users 
        WHERE created_at >= datetime('now', '-1 day')
        ORDER BY created_at DESC
    """)
    recent_users = cursor.fetchall()
    
    print("📈 ACTIVIDAD RECIENTE (Últimas 24 horas)")
    print("=" * 80)
    
    if not recent_users:
        print("❌ No hay actividad reciente")
    else:
        print(f"📊 Usuarios creados: {len(recent_users)}")
        print()
        
        for user in recent_users:
            print(f"👤 {user['name']} ({user['email']})")
            print(f"   📅 Creado: {user['created_at']}")
            print(f"   🔑 Auth0 ID: {user['auth0_id']}")
            print()
    
    conn.close()

def main():
    """Función principal"""
    print("🔧 MONITOR DE USUARIOS MARVELCDB")
    print("=" * 80)
    print("Selecciona una opción:")
    print("1. 📊 Ver usuarios actuales")
    print("2. 🔍 Monitor en tiempo real")
    print("3. 📈 Actividad reciente")
    print("4. 🚪 Salir")
    print()
    
    while True:
        try:
            choice = input("Ingresa tu opción (1-4): ").strip()
            
            if choice == "1":
                clear_screen()
                display_users()
                input("\nPresiona Enter para continuar...")
                clear_screen()
                main()
                break
                
            elif choice == "2":
                clear_screen()
                monitor_changes()
                break
                
            elif choice == "3":
                clear_screen()
                show_recent_activity()
                input("\nPresiona Enter para continuar...")
                clear_screen()
                main()
                break
                
            elif choice == "4":
                print("👋 ¡Hasta luego!")
                break
                
            else:
                print("❌ Opción inválida. Intenta de nuevo.")
                
        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()

