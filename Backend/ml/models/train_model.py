from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report
import pickle
import os
import json
import sys
from datetime import datetime, timezone

# Añadir path para importar prepare_data
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from data.prepare_data import get_training_data, get_db_path

def get_default_model_path() -> str:
    """
    Ruta del modelo:
    - Requiere MODEL_PATH. Si no está definida, se lanza ValueError.
    """
    env_model_path = os.getenv("MODEL_PATH")
    if not env_model_path:
        raise ValueError("MODEL_PATH environment variable is required to save/load the model")
    return env_model_path


def get_metrics_path(model_path: str = None) -> str:
    """Métricas públicas del último entrenamiento, junto al modelo (disco persistente)."""
    model_path = model_path or get_default_model_path()
    return os.path.splitext(model_path)[0] + '_metrics.json'


def _save_public_metrics(model_path, X, y, n_train, n_test, train_score, test_score):
    """Guarda las cifras que muestra la web (/api/model/stats). Nunca rompe el entrenamiento."""
    try:
        rows = [list(row) for row in X]
        metrics = {
            "games": len(rows),
            "wins": int(sum(y)),
            "n_train": int(n_train),
            "n_test": int(n_test),
            "accuracy_train": round(float(train_score), 4),
            "accuracy_test": round(float(test_score), 4),
            # Columnas 0 y 2 de las características: héroe y villano de cada partida
            "heroes": len({row[0] for row in rows}),
            "villains": len({row[2] for row in rows}),
            "trained_at": datetime.now(timezone.utc).isoformat(timespec='seconds'),
        }
        with open(get_metrics_path(model_path), 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2)
    except Exception as e:
        print(f"   (No se pudieron guardar las métricas públicas: {e})")


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
        # No hay datos aún - comportamiento esperado, no mostrar error
        return None
    
    # Verificar que hay al menos 2 partidas (mínimo para dividir train/test)
    if len(X) < 2:
        return None
    
    # Verificar que hay al menos una victoria y una derrota para usar stratify
    unique_classes = len(set(y))
    use_stratify = unique_classes > 1 and len(X) >= 2
    
    print(f"✅ Datos cargados: {len(X)} partidas")
    print(f"   - Features: {len(feature_names)} (4 básicas + 5 características agregadas)")
    print(f"   - Victorias: {sum(y)} ({sum(y)/len(y)*100:.1f}%)")
    print(f"   - Derrotas: {len(y)-sum(y)} ({(len(y)-sum(y))/len(y)*100:.1f}%)")
    
    # Dividir en entrenamiento y prueba (80/20)
    # Usar stratify solo si hay múltiples clases y suficientes datos
    try:
        if use_stratify:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
        else:
            # Sin stratify si solo hay una clase o muy pocos datos
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
    except ValueError as e:
        # Si falla la división (muy pocos datos), no entrenar silenciosamente
        return None
    
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
    
    # Matriz de confusión sobre el 20% de prueba (casos que el modelo no ha visto)
    y_pred = model.predict(X_test)
    cm = confusion_matrix(y_test, y_pred)
    # Clases: 0 = loss (derrota), 1 = win (victoria)
    print("\n📊 Matriz de confusión (conjunto de prueba, 20% no usado en entrenamiento):")
    print("    Filas = resultado real | Columnas = predicción del modelo")
    print("                 Pred. derrota  Pred. victoria")
    print(f"    Real derrota      {cm[0, 0]:>6}           {cm[0, 1]:>6}")
    print(f"    Real victoria     {cm[1, 0]:>6}           {cm[1, 1]:>6}")
    print(f"    → Aciertos: {cm[0, 0] + cm[1, 1]} de {len(y_test)} (precisión prueba: {test_score:.2%})")
    print(classification_report(y_test, y_pred, target_names=["derrota", "victoria"], zero_division=0))
    
    # Guardar matriz de confusión para documentación / memoria
    eval_dir = os.path.join(os.path.dirname(__file__), '..')
    eval_path = os.path.join(eval_dir, "evaluation_confusion_matrix.json")
    try:
        with open(eval_path, 'w', encoding='utf-8') as f:
            json.dump({
                "n_train": len(X_train),
                "n_test": len(X_test),
                "accuracy_train": float(train_score),
                "accuracy_test": float(test_score),
                "confusion_matrix": cm.tolist(),
                "labels": ["derrota", "victoria"]
            }, f, indent=2)
        print(f"   (Matriz guardada en {eval_path})")
    except Exception as e:
        print(f"   (No se pudo guardar matriz: {e})")
    
    # Guardar modelo con metadata
    if model_path is None:
        model_path = get_default_model_path()
    
    # Guardar modelo + feature_names (NO top_cards - se calculan dinámicamente)
    model_data = {
        'model': model,
        'feature_names': feature_names
    }
    
    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)
    
    _save_public_metrics(model_path, X, y, len(X_train), len(X_test), train_score, test_score)

    print(f"💾 Modelo guardado en: {model_path}")
    print(f"   - Usa {len(feature_names)} características generales")
    print(f"   - Las cartas se seleccionan dinámicamente según villano y aspecto")
    
    return model_data


if __name__ == "__main__":
    """
    Punto de entrada para ejecutar el entrenamiento desde línea de comandos:
    python -m ml.models.train_model
    """
    try:
        train_villain_recommender()
    except Exception as e:
        print(f"Error entrenando modelo SVM: {e}")

