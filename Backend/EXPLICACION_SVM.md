# 🤖 Explicación del SVM en el Sistema de Recomendaciones

## 📚 ¿Qué es el SVM?

**SVM (Support Vector Machine)** es un algoritmo de aprendizaje automático que:
1. **Aprende** de datos históricos (partidas jugadas)
2. **Detecta patrones** que no son obvios a simple vista
3. **Predice** probabilidades de victoria para nuevas combinaciones

---

## 🔄 Proceso Completo del SVM

### **1. ENTRENAMIENTO (Una vez, cuando ejecutas `train_model.py`)**

El SVM se entrena con **TODAS las partidas históricas** (203 partidas en tu caso):

```python
# El SVM aprende de:
- Hero_id: Qué héroe se usó
- Aspect: Qué aspecto (aggression, justice, etc.)
- Villain_id: Contra qué villano
- Difficulty: Normal o Expert
- Result: Ganó o perdió
```

**¿Qué aprende el SVM?**
- Patrones generales: "Spider-Man + aggression funciona bien contra villanos rápidos"
- Sinergias: "Protection es mejor en dificultad expert"
- Tendencias: "Algunos héroes funcionan mejor con ciertos aspectos"
- Relaciones complejas entre héroes, aspectos, villanos y dificultades

**Ejemplo de lo que aprende:**
```
Si el SVM ve que:
- Thor + aggression ganó contra Rhino (normal)
- Thor + aggression ganó contra Klaw (normal)
- Thor + aggression ganó contra Ultron (normal)

Entonces aprende: "Thor + aggression tiene alta probabilidad de victoria en normal"
```

---

### **2. PREDICCIÓN (En tiempo real, cuando generas un mazo)**

Cuando pides un mazo para un villano, el SVM:

1. **Recibe** la combinación: `[hero_id, aspect, villain_id, difficulty]`
2. **Usa su conocimiento aprendido** para predecir probabilidad de victoria
3. **Devuelve** un número entre 0 y 1 (ej: 0.65 = 65% probabilidad)

**Ejemplo:**
```python
# Input al SVM:
[Thor_id, aggression, Brotherhood_Of_Badoon_id, normal]

# El SVM piensa:
"Basándome en todas las partidas que he visto:
- Thor + aggression funciona bien en general
- Pero no he visto muchas partidas contra Brotherhood Of Badoon específicamente
- Sin embargo, patrones similares sugieren que podría funcionar"

# Output:
Probabilidad: 0.58 (58%)
```

---

## 🎯 ¿Por qué Combinamos Win Rate Histórico + SVM?

En la función `get_best_hero_aspect_for_villain`, combinamos:

### **Win Rate Histórico (70% del peso)**
- **Qué es**: El porcentaje REAL de victorias de esa combinación contra ese villano específico
- **Ventaja**: Datos concretos y específicos
- **Ejemplo**: "Thor + aggression vs Brotherhood Of Badoon: 0 victorias / 1 partida = 0%"

### **Predicción SVM (30% del peso)**
- **Qué es**: Lo que el SVM predice basándose en patrones generales aprendidos
- **Ventaja**: Puede detectar patrones que no son obvios
- **Ejemplo**: "Aunque no haya ganado contra este villano, el SVM sabe que Thor + aggression funciona bien en general"

### **Score Final**
```python
score = (win_rate_historico * 0.7) + (prediccion_svm * 0.3)
```

**¿Por qué esta combinación?**
- Si hay datos históricos específicos, son más confiables (70%)
- Pero el SVM puede aportar conocimiento general útil (30%)
- Si no hay datos históricos, el SVM puede ayudar

---

## 💡 Ejemplo Práctico

**Escenario**: Quieres un mazo para "Brotherhood Of Badoon" en "normal"

**Datos históricos:**
- Thor + aggression: 0 victorias / 1 partida = 0% win rate
- Tigra + protection: 1 victoria / 1 partida = 100% win rate
- Maria Hill + leadership: 0 victorias / 1 partida = 0% win rate

**Predicciones SVM:**
- Thor + aggression: 0.58 (58%) - El SVM piensa que funciona bien en general
- Tigra + protection: 0.52 (52%) - El SVM no tiene mucha información
- Maria Hill + leadership: 0.45 (45%) - El SVM piensa que no es ideal

**Scores combinados:**
- Thor + aggression: (0.0 * 0.7) + (0.58 * 0.3) = **0.174** ❌
- Tigra + protection: (1.0 * 0.7) + (0.52 * 0.3) = **0.856** ✅
- Maria Hill + leadership: (0.0 * 0.7) + (0.45 * 0.3) = **0.135** ❌

**Resultado**: El sistema recomienda **Tigra + protection** porque:
1. Tiene 100% win rate histórico (muy confiable)
2. El SVM también predice que puede funcionar

---

## 🔍 ¿Qué Hace el SVM Exactamente?

El SVM es como un "experto" que:

1. **Ha visto** todas las partidas históricas (203 partidas)
2. **Ha aprendido** patrones como:
   - "Los héroes con alta defensa funcionan mejor con protection"
   - "Aggression es mejor contra villanos rápidos"
   - "Expert difficulty requiere más defensa"
3. **Puede predecir** para combinaciones nuevas basándose en patrones similares

**Ventajas del SVM:**
- ✅ Detecta patrones complejos que no son obvios
- ✅ Puede generalizar a villanos/héroes nuevos
- ✅ Considera múltiples factores simultáneamente

**Limitaciones:**
- ❌ No puede saber si dos villanos son similares (por eso usamos datos específicos)
- ❌ Puede estar sesgado si hay pocos datos
- ❌ No entiende el "por qué", solo detecta patrones

---

## 📊 Resumen

| Aspecto | Win Rate Histórico | Predicción SVM |
|---------|-------------------|----------------|
| **Fuente** | Partidas específicas contra ese villano | Todas las partidas históricas |
| **Confiabilidad** | Alta (datos reales) | Media (patrones generales) |
| **Peso en decisión** | 70% | 30% |
| **Cuándo es útil** | Cuando hay suficientes partidas | Cuando hay pocos datos específicos |
| **Ejemplo** | "Thor perdió contra este villano" | "Thor funciona bien en general" |

---

## 🎯 Conclusión

El SVM **SÍ aprende** de los datos (cuando lo entrenas) y **SÍ hace predicciones** (cuando generas un mazo).

La combinación de win rate histórico + predicción SVM nos da:
- **Precisión** (de los datos reales)
- **Inteligencia** (de los patrones aprendidos)
- **Robustez** (funciona incluso con pocos datos)

---

## 📈 Pesos Dinámicos (NUEVO)

El sistema ahora ajusta automáticamente los pesos según la cantidad de datos históricos:

### **Con POCOS datos (1-2 partidas)**
- **70% Win Rate Histórico** / **30% Predicción SVM**
- **Razón**: Con tan pocos datos, el win rate específico del villano es más confiable que generalizaciones
- **El histórico tiene más peso** porque es específico de ese villano

### **Con DATOS MEDIOS (3-5 partidas)**
- **50% Win Rate Histórico** / **50% Predicción SVM**
- **Razón**: Balance entre datos específicos y conocimiento general del SVM
- **Balance equitativo**

### **Con MUCHOS datos (6+ partidas)**
- **30% Win Rate Histórico** / **70% Predicción SVM**
- **Razón**: Con más datos de entrenamiento, el SVM ha aprendido mejor patrones y puede generalizar mejor
- **El SVM tiene más peso** porque es la base del TFG y mejora con más datos

### **Ejemplo de Evolución:**

**Escenario 1: Pocos datos (1 partida)**
```
Thor + aggression: 1 victoria / 1 partida = 100% win rate
SVM predice: 58%

Score = (1.0 * 0.7) + (0.58 * 0.3) = 0.874
Pesos: 70% histórico / 30% SVM (pocos datos - confiar más en lo específico)
```

**Escenario 2: Muchos datos (10 partidas)**
```
Thor + aggression: 7 victorias / 10 partidas = 70% win rate
SVM predice: 58%

Score = (0.7 * 0.3) + (0.58 * 0.7) = 0.616
Pesos: 30% histórico / 70% SVM (muchos datos - el SVM ha aprendido mejor)
```

**Conclusión**: Con más datos de entrenamiento, el SVM mejora y tiene más peso en la decisión final. Esto tiene sentido porque el SVM es la base del TFG y aprende de todas las partidas históricas.

