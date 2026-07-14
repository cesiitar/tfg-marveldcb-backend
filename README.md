# AIForge — Backend

API y motor de IA de **AIForge**, mi Trabajo de Fin de Grado: una plataforma web para crear, compartir y optimizar mazos de Marvel Champions usando machine learning. La interfaz está en [tfg-marveldcb-frontend](https://github.com/cesiitar/tfg-marveldcb-frontend) (desplegada en https://aiforge-decks.vercel.app).

## Qué hace

Una API REST en FastAPI (~35 endpoints) que cubre:

- **Catálogo del juego**: cartas, sets, héroes y villanos. La base de datos se monta desde cero con `init_all.py`, que importa todo desde la API pública de [MarvelCDB](https://marvelcdb.com).
- **Mazos**: creación, edición y borrado, comentarios, favoritos e importación de cartas que falten en el catálogo local.
- **Partidas**: registro de configuraciones de juego (héroe/aspecto contra villano/dificultad y resultado), historial y estadísticas por usuario.
- **Usuarios**: la identidad la gestiona Auth0 desde el frontend; el backend sincroniza cada usuario por su id de Auth0.
- **Recomendaciones con IA**: el endpoint estrella. Estima la probabilidad de victoria contra un villano y genera un mazo optimizado para ese enfrentamiento.

## La parte de machine learning

Es el núcleo del TFG y está en `Backend/ml/`:

- Un **SVM (scikit-learn)** que predice la probabilidad de victoria a partir de **9 features generales**: héroe, aspecto, villano y dificultad, más 5 características agregadas del mazo (coste medio y proporciones de eventos, aliados, mejoras y soportes).
- Una decisión de diseño que me costó llegar a ella: **el modelo no usa cartas individuales como features**. Con millones de combinaciones posibles y relativamente pocas partidas, eso solo producía sobreajuste. En su lugar, el modelo trabaja con la "forma" del mazo, y las cartas concretas del mazo recomendado se seleccionan dinámicamente a partir de los mazos ganadores contra ese villano y aspecto.
- El modelo se **reentrena en segundo plano** cada vez que un usuario registra una partida nueva (con `BackgroundTasks` de FastAPI), con división train/test 80/20 estratificada y matriz de confusión para evaluar.

## Stack y despliegue

- **Python 3.11** con **FastAPI** + Uvicorn
- **SQLite** como base de datos (en producción vive en un disco persistente de Render, configurable con `DB_PATH`)
- **scikit-learn, pandas y numpy** para el modelo
- Desplegado en **Render** (`render.yaml`)

## Ejecutarlo en local

```bash
cd Backend
pip install -r requirements.txt
python init_all.py        # descarga el catálogo completo de MarvelCDB (tarda un rato)
uvicorn main:app --reload
```

| Variable | Qué es |
| --- | --- |
| `DB_PATH` | Ruta del fichero SQLite. Opcional: por defecto `Backend/marvel_cards.db` |
| `MODEL_PATH` | Dónde guardar/cargar el modelo entrenado (`.pkl`). Necesaria para la parte de IA |

La documentación interactiva de la API queda en `http://localhost:8000/docs` (Swagger la genera FastAPI solo).

## Sobre este repo

Es mi TFG y está publicado como parte de mi portfolio, para que se pueda leer el código. No tiene licencia de uso: todos los derechos reservados. AIForge es un proyecto académico y de fans, sin ánimo de lucro: Marvel Champions y sus cartas son propiedad de sus respectivos dueños, y los datos se obtienen de la API pública de MarvelCDB.
