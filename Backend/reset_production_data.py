"""
Script para limpiar TODOS los datos de producción antes de desplegar:
- Elimina TODAS las partidas (game_configurations)
- Elimina TODOS los mazos (decks)
- Elimina el modelo SVM entrenado
"""

from reset_ai_training import delete_all_production_data

if __name__ == '__main__':
    print("=" * 60)
    print("🧹 LIMPIEZA DE DATOS DE PRODUCCIÓN")
    print("=" * 60)
    print()
    print("⚠️  ADVERTENCIA: Esto eliminará:")
    print("   - TODAS las partidas")
    print("   - TODOS los mazos")
    print("   - El modelo entrenado")
    print()
    
    response = input("¿Estás seguro de que quieres continuar? (escribe 'SI' para confirmar): ")
    
    if response == 'SI':
        print()
        decks_deleted, games_deleted, model_deleted = delete_all_production_data()
        print()
        print("=" * 60)
        print("🎉 ¡Limpieza completada!")
        print("=" * 60)
        print()
        print("📋 Resumen:")
        print(f"   - Partidas eliminadas: {games_deleted}")
        print(f"   - Mazos eliminados: {decks_deleted}")
        print(f"   - Modelo SVM: {'Eliminado' if model_deleted else 'No existía'}")
        print()
        print("✅ Base de datos lista para producción")
    else:
        print()
        print("❌ Operación cancelada")

