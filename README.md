# 🏎️ F1 Dashboard

Dashboard web interactivo (Taipy + FastF1 + Plotly) para análisis de telemetría y rendimiento de pilotos de Fórmula 1.

## 📊 Funcionalidades

### KPIs de Rendimiento
- **Efficiency Score**: % de tiempo con acelerador a fondo (≥95%)
- **Coast/Lift %**: % de tiempo levantando acelerador sin frenar (detecta pendiente negativa de throttle)

### 🗺️ Mapa del Circuito
Visualización del trazado con eventos marcados:
| Elemento | Color | Descripción |
|----------|-------|-------------|
| **Trazado** | Color del piloto | Línea del circuito basada en coordenadas X,Y |
| **Coast/Lift** | 🟠 Naranja | Zonas levantando acelerador sin frenar |
| **Traction Loss** | 🟣 Magenta | Posible patinaje (RPM sube, velocidad no) |
| **Curvas** | ⚪ Blanco | Diamantes numerados en cada curva |
| **Start/Finish** | 🟢 Verde | Estrella en línea de meta |

### 📈 Telemetría Unificada (4 filas, eje X compartido)
| Fila | Descripción |
|------|-------------|
| **Speed** | Velocidad (km/h) con Coast/Lift (naranja) y Traction Loss (magenta) |
| **Throttle & Brake** | Acelerador (verde) y freno (rojo) con línea de referencia al 95% |
| **RPM** | Revoluciones del motor con Traction Loss marcado |
| **Gear** | Selección de marchas (1-8) |

### 🏁 Análisis de Tiempos
| Gráfico | Descripción |
|---------|-------------|
| **Sector Times** | Tiempos por sector (S1, S2, S3) de todas las vueltas válidas |
| **Pace vs Tyre Age** | Evolución de tiempos + edad del neumático por compuesto |
| **Stint Comparison** | Barras horizontales con tiempo promedio por compuesto |

### 🔍 Detección Automática
- **Coast/Lift**: Pendiente negativa de throttle + throttle < 95% + sin freno
- **Traction Loss**: RPM subiendo > 200 + velocidad estancada + throttle > 50%

### Características
- **Eje X compartido** en telemetría (zoom/pan sincronizado)
- **Marcadores de curvas** del circuito en todos los gráficos
- **Colores por compuesto**: 🔴 Soft, 🟡 Medium, ⚪ Hard, 🟢 Inter, 🔵 Wet
- Soporte para **Qualifying** y **Race**
- Datos desde **2018** hasta la temporada actual

## 🚀 Cómo correr el proyecto

```bash
# Crear ambiente virtual
python3 -m venv env
source env/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python3 main.py
```

El dashboard estará disponible en `http://127.0.0.1:5001`

## 📦 Dependencias principales
- **FastF1**: Acceso a datos oficiales de F1
- **Taipy**: Framework para dashboard interactivo
- **Plotly**: Gráficos interactivos

## 📁 Estructura
```
f1-dashboard/
├── main.py           # Aplicación principal
├── requirements.txt  # Dependencias
├── f1_cache/         # Cache de datos FastF1
└── README.md
```
