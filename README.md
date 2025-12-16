 # F1 Dashboard
 
 Dashboard web (Taipy + FastF1 + Plotly) para visualizar telemetría de Fórmula 1.
 
 ## ¿Qué muestra?
 
 - **Speed Trace**: velocidad (km/h) de la vuelta más rápida del piloto seleccionado.
 - **Throttle & Brake Trace**: acelerador (0-100%, línea verde) y freno (0-100%, línea roja).
 - Ambos gráficos están en un **mismo figure con subplots** y comparten el **eje X (Distancia)**, por lo que el **zoom/pan se sincroniza**.
 
 ## Cómo correr el proyecto
 Para iniciar el proyecto, ejecuta:
 ```bash
 python3 -m venv env
 source env/bin/activate
 pip install -r requirements.txt
 python3 main.py
 ```
 Esto creará un ambiente virtual, instalará las dependencias y ejecutará el proyecto. Por defecto lo levanta en `http://127.0.0.1:5001`
