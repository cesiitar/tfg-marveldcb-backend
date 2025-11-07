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
    Entrena el modelo SVM para predecir probabilidad de victoria
    
    Args:
        db_path: Ruta a la base de datos (opcional, usa la predeterminada si no se proporciona)
        model_path: Ruta donde guardar el modelo (opcional)
    
    Returns:
        Modelo entrenado
    """
    print("📊 Cargando datos de entrenamiento...")
    
    if db_path is None:
        db_path = get_db_path()
    
    try:
        X, y = get_training_data(db_path)
    except ValueError as e:
        print(f"❌ Error: {e}")
        return None
    
    if len(X) < 10:
        print(f"⚠️  No hay suficientes datos para entrenar (mínimo 10 partidas, tienes {len(X)})")
        return None
    
    print(f"✅ Datos cargados: {len(X)} partidas")
    print(f"   - Victorias: {sum(y)} ({sum(y)/len(y)*100:.1f}%)")
    print(f"   - Derrotas: {len(y)-sum(y)} ({(len(y)-sum(y))/len(y)*100:.1f}%)")
    
    # Dividir en entrenamiento y prueba (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print("🤖 Entrenando modelo SVM...")
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
    
    # Guardar modelo
    if model_path is None:
        model_dir = os.path.join(os.path.dirname(__file__), '..', 'saved_models')
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, 'villain_svm_model.pkl')
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    print(f"💾 Modelo guardado en: {model_path}")
    
    return model

if __name__ == '__main__':
    # Entrenar modelo
    model = train_villain_recommender()
    
    if model:
        print("\n🎉 Modelo entrenado exitosamente!")
    else:
        print("\n❌ Error al entrenar el modelo")

