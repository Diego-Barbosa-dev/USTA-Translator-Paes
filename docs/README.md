# Traductor de Lenguas Indígenas

## Descripción General
Esta aplicación web permite la traducción entre español y cuatro lenguas indígenas importantes de Colombia: Sikuani, Piapoco, Achagua y Guayabero. La aplicación está diseñada para preservar y promover estas lenguas indígenas a través de una interfaz intuitiva y accesible.

## Características Principales

### Traducción de Texto
- Traducción bidireccional entre español y lenguas indígenas
- Interfaz simple y fácil de usar
- Normalización de texto para mejorar la precisión
- Mensajes claros cuando una palabra no se encuentra en el diccionario

### Sistema de Retroalimentación
- Los usuarios pueden proporcionar correcciones a las traducciones
- Las correcciones se almacenan en los diccionarios respectivos
- Contribución comunitaria para mejorar la calidad de las traducciones

### Interfaz de Usuario
- Diseño moderno y responsivo
- Selector de idiomas intuitivo
- Área de texto clara para entrada y salida
- Indicadores visuales del estado de la traducción

## Estructura del Proyecto
```
rebecca.1/
├── data/                  # Diccionarios de idiomas
│   ├── sikuani_dictionary.json
│   ├── piapoco_dictionary.json
│   ├── achagua_dictionary.json
│   └── guayabero_dictionary.json
├── docs/                  # Documentación
│   └── README.md
├── models/               # Modelos de traducción
│   └── nllb-200-distilled-600M/
├── src/                  # Código fuente
│   ├── app.py            # Aplicación principal
│   └── learning_model.py # Modelo de aprendizaje
├── static/              # Archivos estáticos
│   ├── app.js           # Lógica del cliente
│   └── style.css        # Estilos
└── templates/           # Plantillas HTML
    └── index.html       # Página principal
```

## Diccionarios de Idiomas

### Sikuani
- Idioma hablado en los llanos orientales de Colombia
- Incluye vocabulario esencial para comunicación básica
- Contiene explicaciones culturales relevantes

### Piapoco
- Lengua arawak hablada en Colombia y Venezuela
- Vocabulario fundamental para interacciones cotidianas
- Incluye términos culturales importantes

### Achagua
- Lengua arawak de los llanos orientales
- Diccionario con términos básicos y culturales
- Enfoque en preservación lingüística

### Guayabero
- Lengua guahibo hablada en el departamento del Meta
- Vocabulario esencial para comunicación básica
- Incluye términos relacionados con su cultura

## Tecnologías Utilizadas

### Backend
- Python con Flask para el servidor web
- Sistema de gestión de diccionarios JSON
- Procesamiento de texto para normalización

### Frontend
- JavaScript para interacciones del cliente
- HTML5 y CSS3 para la interfaz de usuario
- Diseño responsivo para diferentes dispositivos

## Instalación y Ejecución

1. Clonar el repositorio
2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecutar la aplicación:
   ```bash
   python src/app.py
   ```
4. Acceder a la aplicación en `http://localhost:5000`

## Contribución

### Mejora de Traducciones
1. Usar el sistema de retroalimentación en la interfaz
2. Las correcciones se incorporan automáticamente al diccionario
3. Las contribuciones ayudan a mejorar la precisión general

### Desarrollo
1. Fork del repositorio
2. Crear rama para nuevas características
3. Enviar pull request con mejoras

## Licencia
Este proyecto está bajo la Licencia MIT. Ver el archivo LICENSE para más detalles.