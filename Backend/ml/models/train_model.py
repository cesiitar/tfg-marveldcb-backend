from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
import pickle
import os
import sys

# Añadir path para importar prepare_data
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from data.prepare_data import get_training_data, get_db_path

def train_villain_recommender(db_path: str = None, model_path: str = None):
    """
    Entrena el modelo SVM para predecir probabilidad de victoria usando solo características generales
    
    NOTA: El modelo NO usa cartas específicas como features. Las cartas se seleccionan
    dinámicamente durante la generación de mazos según el villano y aspecto específicos.
    
    Args:
        db_path: Ruta a la base de datos (opcional, usa la predeterminada si no se proporciona)
        model_path: Ruta donde guardar el modelo (opcional)
    
    Returns:
        Diccionario con: {'model': modelo, 'feature_names': lista}
    """
    print("📊 Cargando datos de entrenamiento...")
    
    if db_path is None:
        db_path = get_db_path()
    
    try:
        # Obtener datos de entrenamiento (sin top_cards - ya no se usan)
        X, y, feature_names = get_training_data(db_path, top_cards=None)
    except ValueError as e:
        print(f"❌ Error: {e}")
        return None
    
    if len(X) < 10:
        print(f"⚠️  No hay suficientes datos para entrenar (mínimo 10 partidas, tienes {len(X)})")
        return None
    
    print(f"✅ Datos cargados: {len(X)} partidas")
    print(f"   - Features: {len(feature_names)} (4 básicas + 5 características agregadas)")
    print(f"   - Victorias: {sum(y)} ({sum(y)/len(y)*100:.1f}%)")
    print(f"   - Derrotas: {len(y)-sum(y)} ({(len(y)-sum(y))/len(y)*100:.1f}%)")
    
    # Dividir en entrenamiento y prueba (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print("🤖 Entrenando modelo SVM con características generales...")
    model = SVC(
        probability=True,  # Necesario para obtener probabilidades
        kernel='rbf',      # Kernel radial (funciona bien para este tipo de datos)
        random_state=42,
        C=1.0              # Parámetro de regularización
    )
    
    model.fit(X_train, y_train)
    
    # Evaluar modelo
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    
    print(f"✅ Precisión entrenamiento: {train_score:.2%}")
    print(f"✅ Precisión prueba: {test_score:.2%}")
    
    # Guardar modelo con metadata
    if model_path is None:
        model_dir = os.path.join(os.path.dirname(__file__), '..', 'saved_models')
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, 'villain_svm_model.pkl')
    
    # Guardar modelo + feature_names (NO top_cards - se calculan dinámicamente)
    model_data = {
        'model': model,
        'feature_names': feature_names
    }
    
    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)
    
    print(f"💾 Modelo guardado en: {model_path}")
    print(f"   - Usa {len(feature_names)} características generales")
    print(f"   - Las cartas se seleccionan dinámicamente según villano y aspecto")
    
    return model_data

if __name__ == '__main__':
    # Entrenar modelo
    model = train_villain_recommender()
    
    if model:
        print("\n🎉 Modelo entrenado exitosamente!")
    else:
        print("\n❌ Error al entrenar el modelo")

