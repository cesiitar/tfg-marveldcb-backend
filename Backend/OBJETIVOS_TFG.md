# Objetivos del Trabajo de Fin de Grado

## 2. Objetivos

Este capítulo expone los objetivos principales del Trabajo de Fin de Grado, desglosados en un objetivo general y varios objetivos específicos. Además, se incluye una descripción de la evolución del desarrollo del proyecto, que ha seguido un enfoque incremental, basado en la iteración continua y la integración de funcionalidades de manera progresiva.

### 2.1. Objetivo general

El objetivo principal de este proyecto es desarrollar una plataforma web completa para la gestión y recomendación de mazos del juego de cartas Marvel Champions: The Card Game, que integre un sistema de inteligencia artificial basado en Support Vector Machines (SVM) para generar recomendaciones personalizadas de mazos optimizados según el villano y la dificultad seleccionados por el usuario.

### 2.2. Objetivos específicos

Para alcanzar el objetivo general, se han planteado los siguientes objetivos específicos, organizados por área de responsabilidad:

#### Objetivos del Backend

**Desarrollar una API REST completa utilizando FastAPI** que proporcione todos los servicios necesarios para la gestión de usuarios, mazos, partidas y recomendaciones.

**Diseñar e implementar una base de datos SQLite** con integridad referencial mediante Foreign Keys y restricciones `ON DELETE CASCADE` para garantizar la consistencia de los datos.

**Implementar un sistema de autenticación** mediante integración con Auth0 que permita la identificación segura de usuarios y la gestión de sesiones.

**Desarrollar un sistema de inteligencia artificial basado en Support Vector Machines (SVM)** utilizando scikit-learn que aprenda de las partidas históricas de los usuarios para predecir la probabilidad de victoria de combinaciones héroe/aspecto contra villanos específicos.

**Implementar un sistema de entrenamiento automático del modelo de IA** que se ejecute en segundo plano cada vez que se registre una nueva partida, permitiendo que el modelo mejore continuamente con los datos de los usuarios.

**Desarrollar un algoritmo de generación de mazos optimizados** que utilice el modelo SVM entrenado para seleccionar tanto la combinación héroe/aspecto como las cartas específicas más adecuadas para enfrentar un villano determinado.

**Garantizar la persistencia de datos y modelos** mediante el uso de volúmenes persistentes en el entorno de producción, asegurando que tanto la base de datos como el modelo de IA entrenado se mantengan entre reinicios del servidor.

**Aplicar medidas de seguridad básicas** como validación de inputs, control de accesos basado en autenticación, y protección contra operaciones no autorizadas mediante verificación de propiedad de recursos.

#### Objetivos Generales del Proyecto

**Diseñar y desarrollar una aplicación web moderna** en formato SPA (Single Page Application) utilizando tecnologías actuales tanto en frontend como en backend.

**Integrar un sistema de recomendación inteligente** que proporcione sugerencias personalizadas de mazos basadas en el historial de partidas y el aprendizaje automático.

**Implementar funcionalidades de gestión de mazos** que permitan a los usuarios crear, editar, eliminar y compartir sus mazos personalizados.

**Desarrollar un sistema de registro de partidas** que permita a los usuarios documentar sus juegos y resultados, proporcionando datos valiosos para el entrenamiento del modelo de IA.

**Crear un sistema de favoritos y comentarios** que fomente la interacción social entre usuarios y facilite el descubrimiento de mazos populares.

**Garantizar una experiencia de usuario responsive y accesible** desde distintos dispositivos, asegurando que la aplicación funcione correctamente en ordenadores, tablets y móviles.

**Integrar datos actualizados de cartas** mediante la conexión con la API pública de MarvelCDB, asegurando que la plataforma siempre disponga de la información más reciente del juego.

### 2.3. Metodología empleada

El desarrollo del proyecto ha seguido una metodología incremental basada en principios ágiles. Desde las primeras fases, se mantuvo una comunicación constante con el tutor académico, lo cual permitió incorporar feedback de forma continua y ajustar el desarrollo a las necesidades reales del proyecto.

La planificación y ejecución del proyecto se dividieron en entregas parciales, cada una centrada en una funcionalidad clave. El desarrollo comenzó con la estructura básica del backend y la base de datos, seguido de la implementación de los endpoints principales de la API. Posteriormente, se desarrolló el sistema de inteligencia artificial, comenzando con la preparación de datos y el entrenamiento básico del modelo SVM, para luego integrar la generación de recomendaciones. Finalmente, se implementaron las funcionalidades adicionales como favoritos, comentarios y el sistema de entrenamiento automático.

El resumen temporal de estas fases puede verse en la Figura 2.1, que representa visualmente las principales etapas del desarrollo.

**Fases principales del desarrollo:**

- **Definición del proyecto y estudio de tecnologías**: Análisis de requisitos, selección de stack tecnológico (FastAPI, SQLite, scikit-learn) y diseño de la arquitectura general.

- **Desarrollo de la base de datos y estructura básica del backend**: Diseño del esquema de base de datos, implementación de utilidades centralizadas y creación de las tablas principales.

- **Implementación de endpoints básicos de la API**: Desarrollo de endpoints para gestión de usuarios, cartas, sets y mazos, incluyendo autenticación mediante Auth0.

- **Desarrollo del sistema de registro de partidas**: Implementación del endpoint de game configurations y sistema de almacenamiento de resultados de partidas.

- **Implementación del sistema de inteligencia artificial**: Desarrollo del módulo de preparación de datos, entrenamiento del modelo SVM y generación de recomendaciones.

- **Integración del entrenamiento automático**: Implementación del sistema que entrena el modelo automáticamente cuando se registra una nueva partida.

- **Desarrollo de funcionalidades adicionales**: Implementación de favoritos, comentarios y endpoints de estadísticas.

- **Despliegue en producción**: Configuración del entorno en Render.com con volúmenes persistentes y variables de entorno.

- **Pruebas y optimización**: Validación del sistema completo, pruebas del modelo de IA y ajustes de rendimiento.

- **Redacción de la memoria y documentación final**: Documentación técnica completa y preparación de la memoria del TFG.

Durante todo el proceso se siguieron buenas prácticas de desarrollo software, tales como:

- **Uso de control de versiones con Git**: Todo el código se gestiona mediante Git, permitiendo un historial completo de cambios y facilitando la colaboración.

- **Separación de responsabilidades mediante una arquitectura cliente-servidor**: Frontend y backend completamente desacoplados, comunicándose únicamente mediante la API REST.

- **Aplicación de principios de desarrollo seguro**: Validación de inputs en todos los endpoints, control de accesos mediante autenticación Auth0, y verificación de propiedad de recursos antes de operaciones sensibles.

- **Centralización de utilidades comunes**: Funciones de base de datos centralizadas en `db_utils.py` para evitar duplicación de código y mantener consistencia.

- **Documentación del código**: Comentarios y docstrings que explican la funcionalidad de las funciones principales, especialmente en el módulo de inteligencia artificial.

Se ha implementado una clara separación entre el entorno de desarrollo/local y el entorno de producción. En el entorno local, todas las dependencias (base de datos SQLite, modelo de IA, servidor FastAPI) corren en la propia máquina de desarrollo, permitiendo realizar pruebas aisladas y rápidas sin necesidad de conexión a internet para la mayoría de funcionalidades.

En cambio, el entorno de producción se ha desplegado utilizando servicios especializados:

- **El frontend se aloja en Vercel**, facilitando despliegues rápidos y controlados mediante integración con Git.

- **El backend se ejecuta en Render.com**, una plataforma que permite mantener una API FastAPI de forma estable y escalable, con soporte para volúmenes persistentes.

- **La base de datos en producción** se almacena en un volumen persistente de Render (`/data/marvel_cards.db`), asegurando que los datos se mantengan entre reinicios del servidor.

- **El modelo de IA entrenado** se almacena también en el volumen persistente (`/data/saved_models/villain_svm_model.pkl`), permitiendo que el modelo aprendido se mantenga disponible sin necesidad de reentrenar desde cero en cada reinicio.

- **La autenticación de usuarios** se gestiona mediante Auth0, un servicio externo especializado que proporciona seguridad robusta sin necesidad de gestionar credenciales directamente.

Este enfoque facilita la detección temprana de errores, la escalabilidad del sistema y la separación de responsabilidades, asegurando que los cambios en desarrollo no afecten directamente al entorno en producción. Además, el uso de volúmenes persistentes garantiza que tanto los datos de los usuarios como el modelo de IA entrenado se mantengan de forma segura y permanente.

A continuación, en el siguiente capítulo se detallan los aspectos técnicos de la implementación del backend, incluyendo la arquitectura del sistema, el diseño de la base de datos, el sistema de inteligencia artificial y las funcionalidades desarrolladas.

---

**Nota para el estudiante**: La Figura 2.1 mencionada en el texto deberá ser creada por ti mostrando un diagrama temporal de las fases del proyecto. Puedes usar herramientas como draw.io, Lucidchart, o simplemente crear una tabla con las fechas y fases principales de tu desarrollo.

