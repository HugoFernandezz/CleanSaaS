# **Informe de Investigación Técnica: Arquitectura e Implementación de SaaS MVP para Limpieza de Datos**

## **Resumen Ejecutivo**

Este informe técnico detalla la arquitectura, estrategia de implementación y directrices de desarrollo asistido por Inteligencia Artificial para la construcción de un Producto Mínimo Viable (MVP) de software como servicio (SaaS) dedicado a la limpieza de datos. El objetivo central es diseñar un sistema capaz de procesar archivos de gran volumen (hasta 10 GB) mediante un enfoque determinista basado en reglas, excluyendo el uso de algoritmos probabilísticos de IA para el procesamiento de datos, pero utilizando intensivamente modelos de lenguaje (LLM) como agentes de desarrollo mediante la configuración avanzada de cursorrules.

La investigación concluye que la viabilidad técnica y económica del proyecto reside en una arquitectura desacoplada: un backend asíncrono de alto rendimiento (FastAPI), un motor de procesamiento de datos en memoria eficiente y evaluación perezosa (Polars), y una interfaz de usuario optimizada para la visualización de grandes conjuntos de datos (React Virtualized). El informe proporciona no solo la justificación teórica y empírica de estas tecnologías frente a alternativas como Node.js o Pandas, sino también los artefactos de configuración precisos (.cursorrules) necesarios para orquestar a un LLM en la construcción paso a paso del sistema.

## ---

**1\. Análisis Arquitectónico y Selección Estratégica del Stack Tecnológico**

La construcción de un sistema SaaS capaz de ingerir, procesar y exportar archivos CSV de 10 GB impone restricciones severas sobre la gestión de memoria y la latencia de CPU. A diferencia de las aplicaciones web convencionales, donde el cuello de botella suele ser la I/O de red o base de datos, este sistema enfrenta desafíos de computación intensiva ("CPU-bound") y saturación de memoria ("Memory-bound").

### **1.1 Backend: La Disyuntiva entre FastAPI y Node.js**

El ecosistema de desarrollo web moderno a menudo gravita hacia Node.js debido a su modelo de I/O no bloqueante y su vasto ecosistema. Sin embargo, para tareas de procesamiento de datos masivos, la investigación sugiere un cambio de paradigma hacia Python optimizado.

#### **1.1.1 Limitaciones del Modelo de Node.js para Cargas Pesadas**

Node.js opera sobre un "Event Loop" de un solo hilo. Si bien es excelente para manejar miles de conexiones concurrentes ligeras (como chats o APIs REST simples), su rendimiento se degrada significativamente cuando se ejecutan tareas intensivas de CPU, como el análisis de un CSV de 10 millones de filas. Cualquier operación de cálculo bloquea el hilo principal, deteniendo la respuesta a otras peticiones HTTP entrantes.1 Aunque existen soluciones como Worker Threads, la sobrecarga de serialización de datos entre hilos y la falta de bibliotecas de manipulación de "dataframes" nativos de alto rendimiento (comparables a los del ecosistema Python) hacen que Node.js sea subóptimo para el núcleo de procesamiento.1

#### **1.1.2 La Superioridad de FastAPI en Contextos de Datos**

FastAPI se ha seleccionado como la capa de orquestación por tres razones fundamentales respaldadas por la evidencia técnica:

1. **Rendimiento Asíncrono Nativo:** Construido sobre Starlette y Pydantic, FastAPI permite manejar la concurrencia de I/O (subidas de archivos a S3, consultas a bases de datos) de manera tan eficiente como Node.js, utilizando la sintaxis async/await nativa de Python.1  
2. **Integración Directa con C/Rust:** La ventaja crítica es la capacidad de Python para actuar como "pegamento" para bibliotecas de bajo nivel. Mientras que el código de usuario se escribe en Python, la ejecución real del procesamiento de datos ocurre en rutinas optimizadas de Rust (vía Polars), liberando el Global Interpreter Lock (GIL) y permitiendo un paralelismo real multicore que Node.js no puede igualar fácilmente sin arquitecturas complejas de microservicios.3  
3. **Validación de Datos Rigurosa:** El uso de Pydantic v2 proporciona una validación de esquemas extremadamente rápida. Dado que el sistema se basa en reglas definidas por el usuario (JSON), la capacidad de parsear y validar estas reglas estrictamente antes de la ejecución es vital para la estabilidad del sistema.4

### **1.2 El Motor de Datos: Polars frente a Pandas**

La decisión arquitectónica más trascendental de este MVP es el rechazo de Pandas en favor de Polars. Esta elección no es una preferencia sintáctica, sino una necesidad operativa para manejar archivos de 10 GB en infraestructura de bajo costo.

#### **1.2.1 El Problema de la Evaluación Ansiosa (Eager Evaluation)**

Pandas carga todo el conjunto de datos en la memoria RAM (Evaluación Ansiosa). Para un archivo CSV de 10 GB, Pandas requiere típicamente entre 5 y 10 veces esa cantidad en RAM (50GB \- 100GB) para realizar operaciones, debido a la sobrecarga de objetos de Python y la fragmentación de memoria. Esto obligaría a aprovisionar instancias de servidor extremadamente costosas (e.g., AWS EC2 r5.4xlarge), destruyendo la economía del modelo SaaS MVP.6

#### **1.2.2 Polars: Evaluación Perezosa y Streaming**

Polars, escrito en Rust, implementa un motor de consultas con "Lazy Evaluation" (Evaluación Perezosa). Cuando el usuario define una regla de limpieza (ej. "eliminar filas donde edad es nula"), Polars no ejecuta la acción inmediatamente. En su lugar, construye un grafo de computación optimizado. Solo cuando se solicita el resultado final, el motor ejecuta el plan.

Más crucial aún es su capacidad de **Streaming**. Polars puede procesar conjuntos de datos mucho más grandes que la memoria RAM disponible procesando el archivo en "chunks" (trozos). Lee un bloque, aplica las transformaciones y escribe el resultado, manteniendo la huella de memoria baja y constante. Esto permite procesar un archivo de 10 GB en una máquina con solo 2 GB o 4 GB de RAM, reduciendo los costos de infraestructura en un orden de magnitud.6

**Tabla Comparativa de Rendimiento y Arquitectura:**

| Característica | Pandas | Polars | Implicación para el SaaS |
| :---- | :---- | :---- | :---- |
| **Lenguaje Base** | C / Python | Rust | Polars aprovecha instrucciones SIMD modernas para velocidad. |
| **Gestión de Memoria** | Ansiosa (Todo en RAM) | Perezosa / Streaming | Polars permite procesar 10GB de datos en contenedores pequeños (Docker). |
| **Multithreading** | No (Limitado por GIL) | Sí (Nativo) | Polars utiliza todos los núcleos de CPU disponibles para acelerar la limpieza. |
| **Formato de Memoria** | Numpy (antiguo) | Apache Arrow | Polars tiene interoperabilidad de "cero copia" (zero-copy) con otras herramientas. |
| **Optimización** | Manual | Optimizador de Consultas | Polars reordena operaciones (predicate pushdown) para leer menos datos de S3. |
| **Manejo de Strings** | Objetos Python (Lento) | Arrow StringView (Rápido) | Operaciones de texto masivas son drásticamente más rápidas en Polars. |

### **1.3 Interfaz de Usuario: React y Virtualización**

El frontend enfrenta el desafío de mostrar vistas previas de datos masivos sin bloquear el navegador. Un enfoque ingenuo de renderizar una tabla HTML con 100,000 filas congelaría cualquier navegador moderno debido a la sobrecarga del DOM (Document Object Model).

#### **1.3.1 Virtualización del DOM (Windowing)**

La solución adoptada es la "virtualización" o "windowing", utilizando bibliotecas como react-window o @tanstack/react-virtual. Esta técnica renderiza únicamente los elementos visibles en el "viewport" (ventana de visualización) del usuario, más un pequeño buffer. Si la tabla tiene 1 millón de filas pero la pantalla solo puede mostrar 20, el DOM solo contendrá \~25 nodos div. A medida que el usuario hace scroll, el contenido de estos nodos se recicla y reemplaza dinámicamente. Esto garantiza un rendimiento de 60 FPS (cuadros por segundo) independientemente del tamaño total del conjunto de datos.9

#### **1.3.2 Constructor de Reglas (No-Code)**

Para cumplir con el requisito de "No AI" y "Rule-Based", se integra el componente react-querybuilder. Este componente permite a los usuarios construir lógica compleja (ej. (Edad \> 18 Y Ciudad \= 'Madrid') O (Estado \= 'Activo')) mediante una interfaz gráfica de arrastrar y soltar. El componente exporta esta lógica en un formato JSON estructurado (JsonLogic o formato propio) que es agnóstico del lenguaje, permitiendo su transmisión segura al backend para su ejecución.11

## ---

**2\. Arquitectura Detallada del Flujo de Datos (Pipeline)**

El núcleo del sistema no es solo el código, sino cómo fluyen los datos entre el almacenamiento, la memoria y el usuario.

### **2.1 Ingesta de Datos: S3 Multipart Uploads**

La subida de un archivo de 10 GB no puede pasar a través del servidor API (FastAPI) directamente, ya que bloquearía los procesos "worker" y consumiría memoria excesiva en el servidor web. Se implementa el patrón de **URL Prefirmadas (Presigned URLs)** con subida multipartes.

1. **Iniciación:** El cliente (React) solicita al backend permiso para subir un archivo.  
2. **Autorización:** El backend valida la solicitud y genera una serie de URLs prefirmadas de AWS S3, una para cada "parte" del archivo (ej. fragmentos de 50MB).  
3. **Transferencia Directa:** El navegador sube estos fragmentos directamente a S3, evitando el servidor backend por completo.  
4. **Confirmación:** Una vez completadas todas las subidas, el frontend notifica al backend, que ensambla las partes en S3 y registra los metadatos (tamaño, ruta, tipo) en PostgreSQL.13

### **2.2 Motor de Traducción de Reglas (JSON a Polars)**

Este es el componente lógico más crítico. El backend recibe un objeto JSON del frontend y debe convertirlo en código ejecutable de Polars de manera segura (sin usar eval o exec de Python, que son vulnerables a inyecciones de código).

El sistema utiliza un **Parser Recursivo**. Este parser recorre el árbol JSON de reglas:

* Si encuentra un nodo "grupo" (AND/OR), genera una combinación lógica de expresiones Polars (& / |).  
* Si encuentra un nodo "regla" (ej. operador "greater\_than"), busca en un mapa de operadores seguros y genera la expresión correspondiente (pl.col("campo") \> valor).  
* Este enfoque garantiza que solo se ejecuten operaciones permitidas y tipadas, aislando el sistema de comandos maliciosos.15

### **2.3 Ejecución y Persistencia**

Una vez construido el objeto LazyFrame de Polars con todas las transformaciones aplicadas:

1. El sistema invoca lazy\_frame.collect(streaming=True).  
2. Polars comienza a leer el archivo CSV original desde S3 (utilizando s3fs o el soporte nativo de object\_store de Rust).  
3. Aplica filtros y transformaciones en memoria (chunk a chunk).  
4. Escribe el resultado directamente a un nuevo archivo en S3 (formato Parquet recomendado por su eficiencia, o CSV si el usuario lo requiere).8  
5. Actualiza el estado del trabajo en PostgreSQL a "Completado".

## ---

**3\. Estrategia de Desarrollo Asistido por IA: El Protocolo.cursorrules**

Para materializar esta arquitectura compleja utilizando un LLM como agente de desarrollo (dentro del entorno Cursor), no basta con prompts genéricos. Se requiere un sistema de reglas (.cursorrules) que actúe como un "Gerente Técnico", imponiendo restricciones, estilos y patrones de diseño antes de que se escriba una sola línea de código.

### **3.1 Fundamentos de la Estrategia "Chain of Thought" (Cadena de Pensamiento)**

Los LLMs tienden a "alucinar" soluciones simples (como usar Pandas) porque son estadísticamente más probables en su conjunto de entrenamiento. Para contrarrestar esto, las reglas configuran al agente para operar bajo un protocolo de **Cadena de Pensamiento**. Antes de generar código, el agente debe:

1. **Analizar:** Explicitar qué entiende de la tarea.  
2. **Planificar:** Listar los pasos arquitectónicos.  
3. **Cuestionar:** Evaluar si su plan viola alguna restricción de memoria o rendimiento (ej. "¿Estoy usando read\_csv? Si es así, debo corregirlo a scan\_csv").  
4. **Ejecutar:** Solo entonces, escribir el código.

Este proceso reduce drásticamente los errores lógicos y de arquitectura.17

### **3.2 Estructura Modular de Reglas**

Siguiendo las mejores prácticas descubiertas en la investigación, se evita un único archivo monolítico. En su lugar, se utiliza una estructura jerárquica con archivos .mdc (Markdown Configuration) específicos para cada dominio del monorepo.18

## ---

**4\. Implementación Técnica: Los Archivos de Configuración (.cursorrules)**

A continuación, se presentan los archivos de configuración exactos que deben implementarse en la raíz del proyecto para guiar al LLM. Estos archivos encapsulan toda la investigación arquitectónica previa.

### **4.1 Archivo Maestro: .cursorrules (Raíz del Proyecto)**

Este archivo actúa como el punto de entrada global, definiendo la personalidad y las reglas universales.

# **Data Cleaning SaaS MVP \- Master Architecture Rules**

## **1\. Identidad y Protocolo**

Actúas como un Arquitecto de Software Senior especializado en Sistemas Distribuidos de Alto Rendimiento (Python/Rust) y Frontend Moderno.

* **Mentalidad:** Crítica, preventiva y orientada al rendimiento. No aceptas código subóptimo.  
* **Proceso de Pensamiento (CoT):** Antes de escribir cualquier bloque de código, debes generar un monólogo interno (explicito en el chat) donde evalúes:  
  1. ¿Impacta esto el consumo de memoria?  
  2. ¿Es esta operación asíncrona segura?  
  3. ¿Cumple con la arquitectura "Streaming First"?  
* **Restricción Absoluta:** Si detectas una solicitud del usuario que podría causar un desbordamiento de memoria (OOM) o bloquear el Event Loop, debes rechazarla y proponer la alternativa escalable.

## **2\. Estructura del Proyecto (Monorepo)**

El proyecto sigue una estructura estricta. No crees archivos fuera de estas carpetas:  
/root  
/backend (FastAPI, Polars, PostgreSQL, Dockerfiles)  
/frontend (React, Vite, TypeScript, Dockerfiles)  
/infra (Docker Compose, Terraform, Nginx)  
/docs (Documentación de arquitectura)

## **3\. Estándares Técnicos Globales**

* **Tipado Estricto:** 100% de cobertura de Type Hints en Python y TypeScript (Strict Mode). No se permite Any implícito.  
* **Documentación:** Docstrings obligatorios en todas las funciones públicas, detallando los tipos de entrada/salida y las implicaciones de memoria (ej. "Esta función carga datos en memoria" vs "Esta función es perezosa").  
* **Secretos:** Nunca hardcodear credenciales. Todo debe inyectarse vía variables de entorno (.env) validadas por Pydantic Settings.

## **4\. Inclusión de Reglas Específicas**

Carga y aplica inteligentemente las siguientes reglas según el contexto del archivo editado:

* Para archivos en /backend: Aplicar .cursor/rules/backend.mdc  
* Para archivos en /frontend: Aplicar .cursor/rules/frontend.mdc  
* Para lógica de datos: Aplicar .cursor/rules/data-pipeline.mdc

### **4.2 Reglas de Backend: .cursor/rules/backend.mdc**

Define las restricciones críticas para FastAPI y Polars, evitando explícitamente el uso de Pandas.

## ---

**description: Estándares de Backend para FastAPI, Polars y PostgreSQL globs: backend/\*\*/\*.py alwaysApply: true**

# **Reglas de Desarrollo Backend (Python)**

## **1\. Stack Tecnológico**

* **Web Framework:** FastAPI (Async).  
* **Motor de Datos:** Polars (Rust-backed). **PROHIBIDO PANDAS**.  
* **ORM:** SQLAlchemy 2.0 (Async) \+ Alembic para migraciones.  
* **Validación:** Pydantic v2 (modelos estrictos).

## **2\. Patrones de FastAPI**

* **Async First:** Todos los endpoints (path operations) deben ser async def.  
* **Inyección de Dependencias:** Usar Depends() para sesiones de DB, autenticación y servicios.  
* **Manejo de Errores:** Centralizar excepciones en backend/app/core/errors.py. Nunca devolver errores 500 genéricos; mapear excepciones de negocio a códigos HTTP adecuados.

## **3\. Ingeniería de Datos con Polars (CRÍTICO)**

* **Lazy Evaluation por Defecto:**  
  * SIEMPRE usar pl.scan\_csv(), pl.scan\_parquet().  
  * NUNCA usar pl.read\_csv() para archivos de usuario (riesgo de OOM).  
* **Streaming:**  
  * Al materializar resultados (guardar o procesar), usar SIEMPRE collect(streaming=True).  
* **Tipado:** Usar explícitamente pl.LazyFrame en las firmas de funciones.  
* **Optimización:** Aplicar filtros (filter) y selección de columnas (select) lo antes posible en la cadena de operaciones para reducir I/O.

## **4\. Estructura de Código**

* /app/api: Controladores/Routers.  
* /app/core: Configuración, Seguridad, Logging.  
* /app/models: Modelos SQLAlchemy (Tablas).  
* /app/schemas: Modelos Pydantic (DTOs).  
* /app/services: Lógica de negocio (aquí vive el motor de limpieza).

### **4.3 Reglas de Frontend: .cursor/rules/frontend.mdc**

Asegura que la interfaz no colapse ante grandes volúmenes de datos y mantenga la coherencia visual.

## ---

**description: Estándares de Frontend para React, Virtualización y UI globs: frontend/\*\*/\*.{ts,tsx} alwaysApply: true**

# **Reglas de Desarrollo Frontend (React)**

## **1\. Stack Tecnológico**

* **Framework:** React 18+ (Vite).  
* **Lenguaje:** TypeScript.  
* **Estado Remoto:** TanStack Query (React Query) v5.  
* **Estado Local:** Zustand (evitar Redux).  
* **UI Kit:** Shadcn/UI \+ Tailwind CSS.  
* **Formularios:** React Hook Form \+ Zod.

## **2\. Rendimiento y Virtualización**

* **Regla de Oro:** NUNCA renderizar listas de datos crudos (\>50 elementos) directamente en el DOM.  
* **Implementación:**  
  * Usar @tanstack/react-virtual o react-window para todas las tablas de vista previa de datos.  
  * Implementar "Infinite Scrolling" o paginación basada en cursor para la carga de datos desde la API.

## **3\. Constructor de Reglas (Query Builder)**

* Usar react-querybuilder.  
* Configurar la salida en formato JSONLogic o estructura compatible con el parser del backend.  
* Estilar los componentes del builder para que coincidan con el tema de Shadcn/UI (usar Tailwind classes en los props de control).

## **4\. Gestión de Archivos (Uploads)**

* No enviar archivos al backend directamente.  
* Implementar flujo: Solicitar Presigned URL \-\> PUT directo a S3 \-\> Notificar al Backend.  
* Mostrar progreso de subida real.

### **4.4 Reglas del Motor de Datos: .cursor/rules/data-pipeline.mdc**

Este archivo es el cerebro del sistema, definiendo cómo traducir la intención del usuario a código de máquina seguro.

## ---

**description: Lógica de traducción de reglas dinámicas a expresiones Polars globs: backend/app/services/engine/\*\*/\*.py alwaysApply: true**

# **Reglas del Motor de Pipeline de Datos**

## **1\. Objetivo**

Construir un traductor determinista que convierta JSON de reglas (frontend) en un pl.LazyFrame de Polars ejecutable.

## **2\. Seguridad y Parsing**

* **Prohibido:** No usar eval(), exec(), o interpolación de strings SQL/Python directas.  
* **Patrón Interpreter:** Implementar un patrón Visitor/Interpreter que recorra el árbol JSON.  
  * Mapear operador "AND" \-\> pl.col(x) & pl.col(y)  
  * Mapear operador "OR" \-\> pl.col(x) | pl.col(y)  
  * Mapear "contains" \-\> pl.col(x).str.contains(val)  
  * Mapear "is\_null" \-\> pl.col(x).is\_null()

## **3\. Manejo de Tipos**

* El JSON llega como strings/números genéricos. El motor debe inspeccionar el esquema del archivo (LazyFrame.schema) y hacer "casting" explícito antes de comparar.  
* Ejemplo: Si la columna "precio" es Float64 y la regla es \> "100", convertir "100" a float antes de aplicar la máscara.

## **4\. I/O Eficiente**

* Leer de S3 usando credenciales inyectadas (vía variables de entorno o roles IAM).  
* Escribir resultados de manera atómica: Escribir a .tmp/archivo, y al finalizar renombrar a processed/archivo.

## ---

**5\. Guía de Implementación Paso a Paso (Roadmap para el LLM)**

Una vez instalados los archivos .cursorrules, el usuario debe guiar al LLM a través de una secuencia lógica de construcción. Intentar hacer todo de una vez suele resultar en código incoherente. Se propone el siguiente plan de ejecución secuencial:

### **Fase 1: Infraestructura y Boilerplate**

*Instrucción Sugerida:* "Inicializa el monorepo basándote en las reglas maestras. Crea el docker-compose.yml con servicios para FastAPI (backend), PostgreSQL 15 (db), y MinIO (s3-local). Configura la estructura de directorios y los archivos pyproject.toml (Poetry) y package.json."

*Resultado Esperado:* Un entorno funcional donde docker compose up levanta una base de datos y un almacenamiento de objetos local, con el esqueleto de backend y frontend listos.

### **Fase 2: Núcleo del Backend y Modelado de Datos**

*Instrucción Sugerida:* "Implementa el núcleo de FastAPI. Configura SQLAlchemy asíncrono y Alembic. Crea los modelos Project, Dataset y CleaningJob. Implementa los endpoints básicos de salud y configuración de base de datos."

*Resultado Esperado:* Conectividad a la base de datos y tablas creadas. El sistema ya puede rastrear "Proyectos" de limpieza.

### **Fase 3: Sistema de Archivos y S3**

*Instrucción Sugerida:* "Implementa el módulo de gestión de archivos. Necesito endpoints para generar URLs prefirmadas (Presigned URLs) para subida multipartes usando boto3. Crea también el endpoint de callback que registra el archivo en la tabla Dataset una vez subido."

*Resultado Esperado:* Capacidad de subir archivos a MinIO/S3 y tener su registro en Postgres, sin que el archivo toque la RAM del servidor API.

### **Fase 4: El Motor de Limpieza (Polars)**

*Instrucción Sugerida:* "Desarrolla el servicio CleaningEngine. Debe aceptar un dataset\_id y un JSON de reglas. Implementa el parser recursivo que traduce ese JSON a expresiones de Polars. Usa scan\_csv y collect(streaming=True) para leer del S3, procesar y guardar el resultado."

*Resultado Esperado:* La pieza central del sistema. Un servicio aislado capaz de tomar lógica abstracta y aplicarla a archivos físicos de manera eficiente.

### **Fase 5: Frontend y Visualización**

*Instrucción Sugerida:* "Construye la UI de subida de archivos en React. Luego, implementa la vista de 'Preview'. Usa react-query para obtener las primeras 100 filas del dataset y tanstack-virtual para renderizar la tabla de manera eficiente. Integra react-querybuilder para permitir al usuario definir las reglas."

*Resultado Esperado:* Una interfaz visual donde el usuario carga un archivo, ve sus datos, crea reglas visualmente y lanza el proceso.

### **Fase 6: Integración y Ejecución Asíncrona**

*Instrucción Sugerida:* "Conecta el botón 'Limpiar' del frontend con el backend. El backend debe lanzar el proceso de Polars como una BackgroundTask de FastAPI (o usar una cola simple por ahora) y actualizar el estado del CleaningJob. El frontend debe hacer polling del estado hasta que termine."

*Resultado Esperado:* El ciclo completo MVP funcionando.

## ---

**6\. Análisis de Rendimiento y Escalabilidad**

### **6.1 Eficiencia de Memoria y Costos**

La arquitectura propuesta aborda directamente el problema de costos. Un enfoque tradicional con Pandas requeriría instancias de nube con 64GB+ de RAM (costo aprox. $300/mes) para procesar archivos de 10GB. Con Polars en modo Streaming, el pico de memoria se mantiene bajo control (generalmente \<2GB), permitiendo usar instancias económicas o contenedores serverless (costo aprox. $30-$50/mes). Esto representa un ahorro de infraestructura del \~85%.6

### **6.2 Escalabilidad Horizontal**

Al estar el estado desacoplado (S3 para datos, Postgres para metadatos) y el cómputo aislado (FastAPI/Polars), el sistema escala horizontalmente sin fricción. Se pueden añadir más réplicas del contenedor de backend para procesar múltiples trabajos simultáneos sin que compitan por los mismos recursos de memoria global, ya que cada proceso de Polars gestiona su propia memoria independientemente.

### **6.3 Futuro: Vectorización y RAG**

Esta arquitectura deja el camino preparado para funcionalidades de IA futura. Al tener Polars ya integrado, añadir un paso de "Embeddings" (vectorización de texto) para limpieza semántica es trivial. Polars puede interactuar eficientemente con bibliotecas como lance o pgvector, permitiendo en una fase 2 ofrecer limpieza basada en significado (ej. "Eliminar filas que parezcan spam") sin reescribir el núcleo del sistema.20

## ---

**7\. Conclusión**

La investigación confirma que es totalmente viable construir un SaaS de limpieza de datos de alto rendimiento sin depender de cajas negras de IA para el procesamiento lógico. La clave reside en la selección rigurosa de herramientas que priorizan la eficiencia de recursos (Rust/Polars) sobre la facilidad de desarrollo inicial (Node/Pandas). La implementación de los archivos .cursorrules proporcionados garantiza que el desarrollo asistido por IA se adhiera estrictamente a estos principios arquitectónicos, evitando la degradación técnica y asegurando un producto final robusto, mantenible y económicamente eficiente.

*Nota Final: Todos los artefactos de código y configuración presentados en este informe están listos para ser desplegados en un entorno de desarrollo compatible con Cursor IDE.*

#### **Obras citadas**

1. Is FastAPI faster than Node.js? \- Lemon.io, fecha de acceso: diciembre 27, 2025, [https://lemon.io/answers/fastapi/is-fastapi-faster-than-node-js/](https://lemon.io/answers/fastapi/is-fastapi-faster-than-node-js/)  
2. Real world scenario FastAPI vs Node.js k8s cluster benchmarks \- Reddit, fecha de acceso: diciembre 27, 2025, [https://www.reddit.com/r/FastAPI/comments/1hyfuob/real\_world\_scenario\_fastapi\_vs\_nodejs\_k8s\_cluster/](https://www.reddit.com/r/FastAPI/comments/1hyfuob/real_world_scenario_fastapi_vs_nodejs_k8s_cluster/)  
3. Which is better for backend development FastAPI or Node.js (Express)? \#179108 \- GitHub, fecha de acceso: diciembre 27, 2025, [https://github.com/orgs/community/discussions/179108](https://github.com/orgs/community/discussions/179108)  
4. How do you typically structure your project if it includes both frontend and fastapi? \#4344, fecha de acceso: diciembre 27, 2025, [https://github.com/fastapi/fastapi/discussions/4344](https://github.com/fastapi/fastapi/discussions/4344)  
5. FastAPI project structure advice needed \- Reddit, fecha de acceso: diciembre 27, 2025, [https://www.reddit.com/r/FastAPI/comments/1nrne2s/fastapi\_project\_structure\_advice\_needed/](https://www.reddit.com/r/FastAPI/comments/1nrne2s/fastapi_project_structure_advice_needed/)  
6. Pandas vs Polars: Which Data Processor Runs Faster \- Shuttle.dev, fecha de acceso: diciembre 27, 2025, [https://www.shuttle.dev/blog/2025/09/24/pandas-vs-polars](https://www.shuttle.dev/blog/2025/09/24/pandas-vs-polars)  
7. Why I Ditched Pandas for Good: Embracing Polars and SQL-First Workflows \- Kaggle, fecha de acceso: diciembre 27, 2025, [https://www.kaggle.com/discussions/general/585068](https://www.kaggle.com/discussions/general/585068)  
8. Streaming large datasets in Polars | Rho Signal, fecha de acceso: diciembre 27, 2025, [https://www.rhosignal.com/posts/streaming-in-polars/](https://www.rhosignal.com/posts/streaming-in-polars/)  
9. How To Render Large Datasets In React without Killing Performance | Syncfusion Blogs, fecha de acceso: diciembre 27, 2025, [https://www.syncfusion.com/blogs/post/render-large-datasets-in-react](https://www.syncfusion.com/blogs/post/render-large-datasets-in-react)  
10. How to virtualize large lists using react-window \- Gemography, fecha de acceso: diciembre 27, 2025, [https://gemography.com/resources/how-to-virtualize-large-lists-using-react-window](https://gemography.com/resources/how-to-virtualize-large-lists-using-react-window)  
11. React Query Builder | Customizable Filter UI \- Syncfusion, fecha de acceso: diciembre 27, 2025, [https://www.syncfusion.com/react-components/react-query-builder](https://www.syncfusion.com/react-components/react-query-builder)  
12. Export | React Query Builder, fecha de acceso: diciembre 27, 2025, [https://react-querybuilder.js.org/docs/6/utils/export](https://react-querybuilder.js.org/docs/6/utils/export)  
13. Amazon S3 Multipart Uploads with Python | Tutorial \- Filestack Blog, fecha de acceso: diciembre 27, 2025, [https://blog.filestack.com/amazon-s3-multipart-uploads-python-tutorial/](https://blog.filestack.com/amazon-s3-multipart-uploads-python-tutorial/)  
14. python \- Amazon S3 \- multipart upload vs split files-then-upload \- Stack Overflow, fecha de acceso: diciembre 27, 2025, [https://stackoverflow.com/questions/49695718/amazon-s3-multipart-upload-vs-split-files-then-upload](https://stackoverflow.com/questions/49695718/amazon-s3-multipart-upload-vs-split-files-then-upload)  
15. Introduction \- jsonpolars 0.2.1 documentation, fecha de acceso: diciembre 27, 2025, [https://jsonpolars.readthedocs.io/en/0.2.1/01-Introduction/index.html](https://jsonpolars.readthedocs.io/en/0.2.1/01-Introduction/index.html)  
16. Reading and writing files on S3 with Polars | Rho Signal, fecha de acceso: diciembre 27, 2025, [https://www.rhosignal.com/posts/reading-from-s3-with-filters/](https://www.rhosignal.com/posts/reading-from-s3-with-filters/)  
17. Best cursor rules configuration? \- Discussions \- Cursor \- Community ..., fecha de acceso: diciembre 27, 2025, [https://forum.cursor.com/t/best-cursor-rules-configuration/55979](https://forum.cursor.com/t/best-cursor-rules-configuration/55979)  
18. Cursor Rules: Best Practices for Developers | by Ofer Shapira ..., fecha de acceso: diciembre 27, 2025, [https://medium.com/elementor-engineers/cursor-rules-best-practices-for-developers-16a438a4935c](https://medium.com/elementor-engineers/cursor-rules-best-practices-for-developers-16a438a4935c)  
19. Rules | Cursor Docs, fecha de acceso: diciembre 27, 2025, [https://cursor.com/docs/context/rules](https://cursor.com/docs/context/rules)  
20. Uploading and copying objects using multipart upload in Amazon S3 \- AWS Documentation, fecha de acceso: diciembre 27, 2025, [https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html)