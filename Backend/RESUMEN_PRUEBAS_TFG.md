# Resumen: Pruebas del Backend - Capítulo 6

## Pruebas del Backend y Modelo de IA

### 1. Validación de Endpoints REST
**Objetivo**: Verificar que todos los endpoints funcionan correctamente y devuelven los códigos HTTP apropiados.

**Pruebas realizadas**:
- ✅ Comprobación de todos los endpoints con Postman (GET, POST, PUT, DELETE)
- ✅ Validación de códigos de estado HTTP correctos: 200 (éxito), 201 (creado), 400 (error cliente), 401 (no autorizado), 404 (no encontrado), 500 (error servidor)
- ✅ Verificación de estructura JSON de respuestas
- ✅ Validación de manejo de errores con mensajes informativos

**Resultado**: Todos los endpoints funcionan correctamente y manejan adecuadamente los casos de éxito y error.

---

### 2. Integridad de la Base de Datos
**Objetivo**: Garantizar la consistencia y coherencia de los datos mediante restricciones de integridad referencial.

**Pruebas realizadas**:
- ✅ Verificación de Foreign Keys: relaciones entre `users`, `decks`, `game_configurations`, `user_favorites`, `deck_comments`
- ✅ Validación de borrado en cascada (Cascade Delete): al eliminar un usuario se eliminan sus mazos y partidas; al eliminar un mazo se eliminan partidas, comentarios y favoritos asociados
- ✅ Comprobación de que no se generan registros huérfanos en la base de datos
- ✅ Verificación de `PRAGMA foreign_keys = ON` en todas las conexiones

**Resultado**: La integridad referencial funciona correctamente, previniendo inconsistencias y eliminando automáticamente datos relacionados.

### 2.1. Análisis de Estructura de Columnas y Diseño de Base de Datos
**Objetivo**: Estudiar y validar la estructura de las tablas para asegurar que todas las columnas necesarias están presentes y correctamente tipadas.

**Pruebas realizadas**:
- ✅ **Análisis de estructura de cartas**: Ejecución de `analyze_card_structure()` durante la inicialización para inspeccionar todos los campos disponibles en la API de MarvelCDB (pack_code, pack_name, type_code, faction_code, position, etc.)
- ✅ **Verificación de columnas con PRAGMA**: Uso de `PRAGMA table_info()` para verificar dinámicamente qué columnas existen en cada tabla antes de realizar operaciones
- ✅ **Migración dinámica de columnas**: Verificación y creación automática de columnas faltantes en `cards` (marvelcdb_code, deck_limit, health, attack, threat, traits, text, is_unique) y en `decks` (hero_name, aspect, is_public, description, hero_id, user_id)
- ✅ **Estandarización de tipos de datos**: Migración de `user_id` de `TEXT` a `INTEGER` en tablas existentes para garantizar consistencia y eficiencia en las relaciones
- ✅ **Uso de IDs como identificadores únicos**: Validación de que todas las operaciones de edición y visualización se basan en IDs numéricos (INTEGER PRIMARY KEY) en lugar de nombres, garantizando unicidad y rendimiento

**Resultado**: El sistema analiza automáticamente la estructura de datos y adapta el esquema de la base de datos según sea necesario, garantizando que todas las columnas requeridas existan antes de realizar operaciones. El uso de IDs numéricos como identificadores primarios permite operaciones eficientes de edición y visualización de cualquier mazo o carta.

---

### 3. Importación de Mazos desde MarvelCDB
**Objetivo**: Verificar que el sistema puede importar mazos públicos desde la página oficial de MarvelCDB para enriquecer la base de datos inicial.

**Pruebas realizadas**:
- ✅ **Obtención de mazos populares**: Verificación de la función `fetch_popular_decks()` que consulta el endpoint `/api/public/decklists/popular/` de MarvelCDB
- ✅ **Procesamiento de estructura de mazos**: Validación del parsing de la estructura JSON de mazos (decklist, meta, slots) recibida desde la API oficial
- ✅ **Conversión de códigos a nombres**: Verificación de la función `get_card_name_by_code()` que convierte códigos de cartas (ej: "01001") a nombres legibles usando la base de datos local
- ✅ **Importación de mazos**: Validación de la función `import_decks()` que inserta mazos públicos en la tabla `decks` con información completa (nombre, descripción, héroe, aspecto, lista de cartas en JSON, flag is_public)
- ✅ **Manejo de errores**: Comprobación de que el sistema maneja correctamente errores de conexión o datos inválidos durante la importación

**Resultado**: El sistema puede importar mazos públicos desde MarvelCDB correctamente, aunque esta funcionalidad quedó deshabilitada en producción para evitar importar datos no deseados al inicio. La infraestructura está lista para ser activada cuando sea necesario.

---

### 4. Sistema de Entrenamiento Automático del Modelo SVM
**Objetivo**: Validar que el modelo de IA se reentrena automáticamente y persiste correctamente en producción.

**Pruebas realizadas**:
- ✅ Verificación de reentrenamiento automático tras registrar nuevas partidas (BackgroundTasks)
- ✅ Validación de persistencia del modelo en archivos `.pkl` en volumen persistente (`/data`)
- ✅ Comprobación de que el modelo persiste tras reinicios del servicio en Render.com
- ✅ Verificación de carga correcta del modelo para generar recomendaciones
- ✅ Validación de cálculo de precisión del modelo (train/test split 80/20)

**Resultado**: El modelo se reentrena automáticamente con nuevas partidas y persiste correctamente en producción, manteniéndose disponible tras reinicios.

---

### 5. Validación de Entradas y Reglas de Negocio
**Objetivo**: Asegurar que los datos recibidos cumplen con las reglas del sistema.

**Pruebas realizadas**:
- ✅ Validación de campos requeridos en creación de mazos y partidas
- ✅ Verificación de formatos: `aspect` (aggression, justice, leadership, protection, pool), `difficulty` (normal, expert), `result` (win, loss)
- ✅ Validación de cantidad de cartas en mazos (40-50 cartas, excluyendo héroe)
- ✅ Verificación de nombres únicos de mazos (case-insensitive)
- ✅ Comprobación de existencia de cartas y villanos en la BD antes de operaciones

**Resultado**: Todas las validaciones funcionan correctamente, rechazando datos inválidos con mensajes de error claros.

---

### 6. Pruebas de Despliegue en Producción
**Objetivo**: Verificar que el sistema funciona correctamente en el entorno de producción (Render.com).

**Pruebas realizadas**:
- ✅ Configuración de volumen persistente para base de datos y modelo (`/data`)
- ✅ Verificación de variables de entorno (`DB_PATH`, `MODEL_PATH`)
- ✅ Validación de inicialización automática de tablas al arrancar la aplicación
- ✅ Comprobación de importación de cartas desde MarvelCDB (1955+ cartas)
- ✅ Verificación de configuración CORS para comunicación con frontend

**Resultado**: El sistema se despliega correctamente en producción, con persistencia de datos y modelo garantizada.

---

## Resumen Ejecutivo

Se realizaron pruebas exhaustivas del backend validando: **endpoints REST** (códigos HTTP y respuestas), **integridad de base de datos** (Foreign Keys, Cascade Delete, análisis de estructura de columnas y uso de IDs como identificadores únicos), **importación de mazos desde MarvelCDB** (infraestructura lista para importar mazos públicos), **entrenamiento automático del modelo SVM** (reentrenamiento y persistencia), **validación de entradas** (reglas de negocio y formatos), y **despliegue en producción** (Render.com con volúmenes persistentes). Todas las pruebas fueron exitosas, confirmando que el sistema es robusto y funcional en producción.
