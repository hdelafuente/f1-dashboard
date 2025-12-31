# 🏎️ F1 Dashboard

Dashboard web interactivo (Taipy + FastF1 + Plotly) para análisis de telemetría y rendimiento de pilotos de Fórmula 1.

## 📊 Funcionalidades

### KPIs de Rendimiento
- **Efficiency Score**: % de tiempo con acelerador a fondo (≥95%)
- **Coast/Lift %**: % de tiempo levantando acelerador sin frenar (detecta pendiente negativa de throttle)

### Gráfico Unificado de Telemetría (4 filas, eje X compartido)

| Fila | Descripción |
|------|-------------|
| **Speed** | Velocidad (km/h) con zonas de Coast/Lift marcadas en naranja |
| **Throttle & Brake** | Acelerador (verde) y freno (rojo) con línea de referencia al 95% |
| **RPM** | Revoluciones del motor |
| **Gear** | Selección de marchas (1-8) |

### Gráficos Adicionales
| Gráfico | Descripción |
|---------|-------------|
| **Sector Times** | Tiempos por sector (S1, S2, S3) de todas las vueltas válidas |
| **Lap Time Evolution** | Evolución de tiempos por vuelta con vuelta rápida destacada |

### Características
- **Eje X compartido** en telemetría (zoom/pan sincronizado en Speed, Throttle, RPM, Gear)
- **Marcadores de curvas** del circuito en todos los gráficos
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
