# Mensaje para Frontend: Importación Automática de Cartas desde MarvelCDB

## Contexto

Cuando un usuario importa un mazo desde MarvelCDB, puede que algunas cartas no estén en nuestra base de datos, lo que causa que la creación del mazo falle. Para solucionar esto, el backend ahora puede importar automáticamente las cartas faltantes desde la API pública de MarvelCDB.

## Endpoints Disponibles

### 1. Importar Cartas Faltantes
**POST** `/api/cards/import-missing`

**Headers:**
```
Content-Type: application/json
X-Auth0-ID: {auth0_id}  // Opcional, pero recomendado
```

**Request Body:**
```json
{
  "card_codes": ["01001", "01002", "01003"]
}
```

**Response (éxito):**
```json
{
  "imported": 3,
  "failed": 0,
  "skipped": 0,
  "message": "3 cartas importadas exitosamente"
}
```

**Response (error):**
```json
{
  "imported": 1,
  "failed": 2,
  "skipped": 0,
  "message": "1 carta importada, 2 fallaron",
  "errors": [
    {
      "code": "01002",
      "error": "Carta no encontrada en MarvelCDB"
    }
  ]
}
```

### 2. (Opcional) Verificar Cartas Faltantes
**POST** `/api/cards/check-missing`

**Request Body:**
```json
{
  "card_codes": ["01001", "01002", "01003"]
}
```

**Response:**
```json
{
  "missing": ["01001", "01002"],
  "existing": ["01003"],
  "total_checked": 3
}
```

## Qué Tiene Que Hacer el Frontend

### Opción A: Manejo de Errores (Recomendada - Más Simple)

Cuando el frontend importa un mazo desde MarvelCDB, ya tiene acceso a los `codes` de las cartas. Si la creación del mazo falla porque faltan cartas, el frontend puede importarlas automáticamente.

**Flujo:**
1. Usuario importa mazo desde MarvelCDB
2. Frontend intenta crear el mazo en el backend
3. Si falla con error "does not exist", extraer los `codes` de las cartas del mazo
4. Llamar a `POST /api/cards/import-missing` con esos `codes`
5. Intentar crear el mazo de nuevo

**Ejemplo de código:**
```javascript
async function importDeckFromMarvelCDB(deckData) {
  try {
    // Intentar crear el mazo directamente
    const response = await createDeck(deckData);
    return response;
  } catch (error) {
    // Si falla porque faltan cartas
    if (error.message?.includes("does not exist") || error.detail?.includes("does not exist")) {
      console.log("Algunas cartas no existen, importándolas...");
      
      // Extraer los codes de las cartas del mazo (MarvelCDB los proporciona)
      const cardCodes = deckData.cards
        .map(card => card.code || card.card_id) // Ajustar según tu estructura
        .filter(code => code); // Filtrar códigos válidos
      
      if (cardCodes.length > 0) {
        // Importar las cartas faltantes
        const importResponse = await fetch('/api/cards/import-missing', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Auth0-ID': getAuth0Id() // Si usas autenticación
          },
          body: JSON.stringify({
            card_codes: cardCodes
          })
        });
        
        const importResult = await importResponse.json();
        console.log(`Importadas ${importResult.imported} cartas`);
        
        // Intentar crear el mazo de nuevo
        return await createDeck(deckData);
      }
    }
    
    // Si no es un error de cartas faltantes, lanzar el error original
    throw error;
  }
}
```

### Opción B: Verificación Previa (Más Controlado)

Verificar qué cartas faltan antes de intentar crear el mazo.

**Flujo:**
1. Usuario importa mazo desde MarvelCDB
2. Frontend verifica qué cartas faltan llamando a `POST /api/cards/check-missing`
3. Si hay cartas faltantes, llamar a `POST /api/cards/import-missing`
4. Crear el mazo normalmente

**Ejemplo de código:**
```javascript
async function importDeckFromMarvelCDB(deckData) {
  // Extraer los codes de las cartas
  const cardCodes = deckData.cards
    .map(card => card.code || card.card_id)
    .filter(code => code);
  
  if (cardCodes.length > 0) {
    // 1. Verificar qué cartas faltan (opcional)
    const checkResponse = await fetch('/api/cards/check-missing', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Auth0-ID': getAuth0Id()
      },
      body: JSON.stringify({
        card_codes: cardCodes
      })
    });
    
    const checkResult = await checkResponse.json();
    
    // 2. Si hay cartas faltantes, importarlas
    if (checkResult.missing && checkResult.missing.length > 0) {
      console.log(`Importando ${checkResult.missing.length} cartas faltantes...`);
      
      const importResponse = await fetch('/api/cards/import-missing', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Auth0-ID': getAuth0Id()
        },
        body: JSON.stringify({
          card_codes: checkResult.missing
        })
      });
      
      const importResult = await importResponse.json();
      console.log(`Importadas ${importResult.imported} cartas`);
      
      if (importResult.failed > 0) {
        console.warn(`${importResult.failed} cartas no se pudieron importar`);
      }
    }
  }
  
  // 3. Crear el mazo (ahora todas las cartas deberían existir)
  return await createDeck(deckData);
}
```

## Estructura de Datos del Mazo desde MarvelCDB

Cuando importas un mazo desde MarvelCDB, normalmente recibes algo como:

```json
{
  "name": "Nombre del Mazo",
  "hero_name": "Spider-Man",
  "aspect": "aggression",
  "cards": [
    {
      "code": "01001",  // ← Este es el código que necesitas
      "name": "Spider-Man",
      "quantity": 1
    },
    {
      "code": "01002",
      "name": "Web-Shooter",
      "quantity": 2
    }
    // ...
  ]
}
```

**Importante:** El campo `code` es el identificador único de MarvelCDB que necesitas pasar al endpoint de importación.

## Consideraciones

1. **Performance:** Si el mazo tiene muchas cartas nuevas, la importación puede tardar unos segundos (el backend hace una petición HTTP por cada carta a MarvelCDB).

2. **Errores:** Si alguna carta no se puede importar (por ejemplo, no existe en MarvelCDB), el endpoint retornará cuántas fallaron pero no bloqueará la creación del mazo si otras cartas sí se importaron.

3. **Duplicados:** El backend evita duplicados automáticamente. Si una carta ya existe, se omite sin error.

4. **Feedback al Usuario:** Es recomendable mostrar un mensaje al usuario mientras se importan las cartas:
   ```javascript
   // Ejemplo con feedback
   showLoadingMessage("Importando cartas faltantes...");
   await importMissingCards(cardCodes);
   hideLoadingMessage();
   showSuccessMessage("Cartas importadas exitosamente");
   ```

## Preguntas Frecuentes

**P: ¿Qué pasa si el código de la carta no existe en MarvelCDB?**  
R: El backend retornará un error para esa carta específica, pero seguirá importando las demás.

**P: ¿Puedo importar todas las cartas de una vez?**  
R: Sí, puedes pasar todos los `codes` en un solo request. El backend las procesará secuencialmente.

**P: ¿Qué pasa si intento importar una carta que ya existe?**  
R: Se omite automáticamente (no se duplica). El contador `skipped` te dirá cuántas se omitieron.

**P: ¿Necesito autenticación?**  
R: El endpoint acepta el header `X-Auth0-ID` pero no es estrictamente necesario. Sin embargo, es recomendable incluirlo si tu aplicación usa autenticación.

## Ejemplo Completo

```javascript
// Función completa de importación de mazo
async function importDeckFromMarvelCDB(marvelCDBDeckData) {
  try {
    // 1. Preparar datos del mazo en nuestro formato
    const deckData = {
      name: marvelCDBDeckData.name,
      hero_name: marvelCDBDeckData.hero_name,
      aspect: marvelCDBDeckData.aspect,
      description: marvelCDBDeckData.description || "",
      cards: marvelCDBDeckData.cards.map(card => ({
        card_id: parseInt(card.code), // Convertir code a número
        card_name: card.name,
        quantity: card.quantity || 1,
        card_set: card.set || "" // Si MarvelCDB lo proporciona
      }))
    };
    
    // 2. Extraer códigos de las cartas
    const cardCodes = marvelCDBDeckData.cards
      .map(card => card.code)
      .filter(code => code);
    
    // 3. Importar cartas faltantes (si las hay)
    if (cardCodes.length > 0) {
      const importResponse = await fetch('/api/cards/import-missing', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Auth0-ID': getAuth0Id()
        },
        body: JSON.stringify({
          card_codes: cardCodes
        })
      });
      
      if (!importResponse.ok) {
        throw new Error("Error al importar cartas");
      }
      
      const importResult = await importResponse.json();
      console.log(`Importadas ${importResult.imported} cartas`);
    }
    
    // 4. Crear el mazo
    const createResponse = await fetch('/api/decks', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Auth0-ID': getAuth0Id()
      },
      body: JSON.stringify(deckData)
    });
    
    if (!createResponse.ok) {
      const error = await createResponse.json();
      throw new Error(error.detail || "Error al crear el mazo");
    }
    
    return await createResponse.json();
    
  } catch (error) {
    console.error("Error importando mazo:", error);
    throw error;
  }
}
```

## Resumen

**Lo que el frontend necesita hacer:**
1. ✅ Tener los `codes` de las cartas del mazo importado (MarvelCDB los proporciona)
2. ✅ Llamar a `POST /api/cards/import-missing` con esos `codes` antes de crear el mazo
3. ✅ Crear el mazo normalmente después de importar

**Lo que NO necesita hacer el frontend:**
- ❌ Obtener datos de cartas desde MarvelCDB (el backend lo hace)
- ❌ Mapear campos de cartas (el backend lo hace)
- ❌ Manejar sets, deck_limit, etc. (el backend lo hace)

¿Es viable para el frontend? Si hay alguna duda o necesitas ajustar algo, avísame.

