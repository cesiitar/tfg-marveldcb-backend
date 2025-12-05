# Documentación para Frontend: Campos de Cartas y Búsqueda

## 📋 Campos Mínimos Requeridos

Cuando el frontend necesita pasar una carta que no existe en nuestra BD, debe proporcionar **al menos estos campos**:

### Campos OBLIGATORIOS:
- **`code`** (string): Código de MarvelCDB (ej: "01001", "01002") - **SIEMPRE REQUERIDO**

### Campos RECOMENDADOS (para mapeo correcto):
- **`name`** (string): Nombre de la carta
- **`type_code`** (string): Tipo de carta (ej: "hero", "ally", "event", "upgrade", "support")
- **`faction_code`** (string): Aspecto/clase de la carta (ej: "aggression", "justice", "leadership", "protection", "pool", "basic", "hero")

### Campos OPCIONALES (pero recomendados si están disponibles):
- **`pack_code`** (string): Código del pack (ej: "core", "msm")
- **`pack_name`** (string): Nombre del pack (ej: "Core Set", "Ms. Marvel")
- **`cost`** (int): Coste de la carta (default: 0)
- **`deck_limit`** (int): Límite de copias por mazo (default: 3)
- **`health`** (int): Salud (para villanos/minions)
- **`attack`** (int): Ataque (para villanos/minions)
- **`threat`** (int): Amenaza (para schemes)
- **`scheme`** (int): Alternativa a `threat` (para schemes)
- **`traits`** (string): Traits de la carta (ej: "Avenger. Champion.")
- **`text`** (string): Texto de la carta
- **`is_unique`** (bool): Si la carta es única
- **`quantity`** (int): Cantidad en el mazo (default: 1)
- **`card_set_name`** (string): Nombre del set de la carta (ej: "Spider-Man", "Ms. Marvel")

## 🔍 Búsqueda de Cartas: Code vs ID

### ⚠️ IMPORTANTE: Code ≠ ID

- **`code` de MarvelCDB**: String con ceros a la izquierda (ej: "01001", "01002")
- **`id` en nuestra BD**: Entero sin ceros a la izquierda (ej: 1001, 1002)

### Conversión de Code a ID

El backend convierte automáticamente el `code` a `id` usando esta lógica:

```javascript
// Función de conversión (para referencia del frontend)
function convertCodeToId(code) {
  if (!code) return null;
  
  const codeStr = String(code);
  
  // Si el code es numérico, convertir a entero (pierde ceros a la izquierda)
  if (/^\d+$/.test(codeStr)) {
    return parseInt(codeStr, 10);
  }
  
  // Si no es numérico, usar hash (no debería pasar con códigos de MarvelCDB)
  // Esto es solo para referencia, el backend lo hace automáticamente
  return null; // El backend usa: abs(hash(code)) % 1000000
}
```

**Ejemplos:**
- `"01001"` → `1001`
- `"01002"` → `1002`
- `"01050"` → `1050`
- `"12345"` → `12345`

### Endpoints de Búsqueda

#### 1. Buscar por Code (RECOMENDADO)
```
GET /api/cards/marvelcdb-code/{code}
```

**Ejemplo:**
```
GET /api/cards/marvelcdb-code/01001
```

**Respuesta (200):**
```json
{
  "id": 1001,
  "name": "Spider-Man",
  "clase": "hero",
  "type": "hero",
  "cost": 0,
  "set": "Core Set",
  "max_quantity": 1,
  "marvelcdb_code": "01001"
}
```

**Respuesta (404):**
```json
{
  "detail": "Carta no encontrada"
}
```

#### 2. Buscar por ID (FALLBACK - No recomendado)
```
GET /api/cards/{id}
```

**⚠️ NO USAR ESTE MÉTODO** porque:
- El frontend trabaja con `code` (string), no con `id` (número)
- Puede haber confusión con los ceros a la izquierda
- El backend ya maneja la conversión automáticamente

### ¿Qué pasa si falla la búsqueda por Code?

El endpoint `GET /api/cards/marvelcdb-code/{code}` tiene un **fallback automático**:

1. **Primero**: Busca por `marvelcdb_code = code` (método preferido)
2. **Si no encuentra**: Convierte el `code` a `id` y busca por `id` (fallback)

**El frontend NO necesita hacer nada especial** - el backend maneja esto automáticamente.

## 📤 Importar Cartas Faltantes

### Endpoint: `POST /api/cards/import-missing`

El frontend puede pasar las cartas de dos formas:

#### Opción 1: Solo códigos (backend busca desde MarvelCDB)
```json
{
  "card_codes": ["01001", "01002"]
}
```

#### Opción 2: Datos completos (recomendado si ya los tienes)
```json
{
  "cards": [
    {
      "code": "01001",
      "name": "Spider-Man",
      "type_code": "hero",
      "faction_code": "hero",
      "pack_code": "core",
      "pack_name": "Core Set",
      "cost": 0,
      "deck_limit": 1,
      "health": 14,
      "attack": 1,
      "traits": "Avenger. Champion.",
      "text": "You can only include hero cards...",
      "is_unique": true,
      "quantity": 1,
      "card_set_name": "Spider-Man"
    }
  ]
}
```

#### Opción 3: Ambos (códigos + datos completos)
```json
{
  "card_codes": ["01001"],
  "cards": [
    {
      "code": "01002",
      "name": "Black Cat",
      "type_code": "ally",
      "faction_code": "hero",
      ...
    }
  ]
}
```

## 🔄 Flujo Recomendado para el Frontend

### Cuando importas un mazo desde MarvelCDB:

1. **Obtener el mazo desde MarvelCDB** (ya tienes todos los datos de las cartas)
2. **Verificar qué cartas faltan:**
   ```javascript
   const missingCodes = deck.cards
     .map(card => card.code)
     .filter(code => code);
   
   const checkResponse = await fetch('/api/cards/check-missing', {
     method: 'POST',
     body: JSON.stringify({ card_codes: missingCodes })
   });
   
   const { missing } = await checkResponse.json();
   ```

3. **Importar cartas faltantes con datos completos:**
   ```javascript
   if (missing.length > 0) {
     // Usar los datos que ya tienes del mazo de MarvelCDB
     const cardsToImport = deck.cards
       .filter(card => missing.includes(card.code))
       .map(card => ({
         code: card.code,
         name: card.name,
         type_code: card.type_code,
         faction_code: card.faction_code,
         pack_code: card.pack_code,
         pack_name: card.pack_name,
         cost: card.cost || 0,
         deck_limit: card.deck_limit,
         health: card.health,
         attack: card.attack,
         threat: card.threat || card.scheme,
         traits: Array.isArray(card.traits) ? card.traits.join(', ') : card.traits,
         text: card.text,
         is_unique: card.is_unique || false,
         quantity: card.quantity || 1,
         card_set_name: card.card_set_name || card.pack_name
       }));
     
     await fetch('/api/cards/import-missing', {
       method: 'POST',
       body: JSON.stringify({ cards: cardsToImport })
     });
   }
   ```

4. **Crear el mazo:**
   ```javascript
   // Ahora todas las cartas existen, crear el mazo
   await fetch('/api/decks', {
     method: 'POST',
     body: JSON.stringify({
       name: deck.name,
       hero_name: deck.hero_name,
       aspect: deck.aspect,
       cards: deck.cards.map(card => ({
         card_id: parseInt(card.code), // Convertir code a id para el mazo
         card_name: card.name,
         quantity: card.quantity || 1,
         clase: card.faction_code, // Aspecto de MarvelCDB
         type: card.type_code,
         set: card.pack_name || card.card_set_name
       }))
     })
   });
   ```

## ⚠️ Notas Importantes

1. **Siempre usar `code` (string)**: El frontend debe trabajar con `code` de MarvelCDB, no con `id`
2. **Conversión automática**: El backend convierte `code` → `id` automáticamente, el frontend no necesita hacerlo
3. **Fallback automático**: Si la búsqueda por `marvelcdb_code` falla, el backend busca por `id` automáticamente
4. **Campos mínimos**: Al importar, solo `code` es obligatorio, pero `name`, `type_code` y `faction_code` son muy recomendados
5. **Datos completos**: Si ya tienes los datos del mazo de MarvelCDB, pásalos directamente en `cards` - es más eficiente

## 📝 Ejemplo Completo

```javascript
// Ejemplo: Importar mazo desde MarvelCDB
async function importDeckFromMarvelCDB(marvelCDBDeck) {
  // 1. Extraer códigos de cartas
  const cardCodes = marvelCDBDeck.cards
    .map(card => card.code)
    .filter(code => code);
  
  // 2. Verificar qué cartas faltan
  const checkResponse = await fetch('/api/cards/check-missing', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ card_codes: cardCodes })
  });
  
  const { missing, existing } = await checkResponse.json();
  
  // 3. Si hay cartas faltantes, importarlas con datos completos
  if (missing.length > 0) {
    const cardsToImport = marvelCDBDeck.cards
      .filter(card => missing.includes(card.code))
      .map(card => ({
        code: card.code,
        name: card.name,
        type_code: card.type_code,
        faction_code: card.faction_code,
        pack_code: card.pack_code,
        pack_name: card.pack_name,
        cost: card.cost ?? 0,
        deck_limit: card.deck_limit,
        health: card.health,
        attack: card.attack,
        threat: card.threat ?? card.scheme,
        traits: Array.isArray(card.traits) ? card.traits.join(', ') : card.traits,
        text: card.text,
        is_unique: card.is_unique ?? false,
        quantity: card.quantity ?? 1,
        card_set_name: card.card_set_name ?? card.pack_name
      }));
    
    const importResponse = await fetch('/api/cards/import-missing', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cards: cardsToImport })
    });
    
    const importResult = await importResponse.json();
    console.log(`Importadas ${importResult.imported} cartas`);
  }
  
  // 4. Crear el mazo (todas las cartas ya existen)
  const deckResponse = await fetch('/api/decks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: marvelCDBDeck.name,
      hero_name: marvelCDBDeck.hero_name,
      aspect: marvelCDBDeck.aspect,
      description: marvelCDBDeck.description || '',
      cards: marvelCDBDeck.cards.map(card => ({
        card_id: parseInt(card.code), // Backend convierte code a id
        card_name: card.name,
        quantity: card.quantity || 1,
        clase: card.faction_code, // Aspecto de MarvelCDB
        type: card.type_code,
        set: card.pack_name || card.card_set_name || ''
      }))
    })
  });
  
  return await deckResponse.json();
}
```

