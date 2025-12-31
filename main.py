import os
import logging
import warnings
from datetime import datetime

import fastf1
import fastf1.plotting
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from taipy.gui import Gui, notify, builder as tgb

# Configuración inicial
warnings.filterwarnings('ignore')
for logger in ['fastf1', 'fastf1.core', 'fastf1.api', 'fastf1.req', 'fastf1._api']:
    logging.getLogger(logger).setLevel(logging.CRITICAL)

CACHE_DIR = 'f1_cache'
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)
fastf1.plotting.setup_mpl(mpl_timedelta_support=True,
                          misc_mpl_mods=False, color_scheme='fastf1')

FALLBACK_COLORS = ['#0600EF', '#FF8700', '#FF1801', '#DC143C', '#00D2BE',
                   '#FF69B4', '#32CD32', '#FF4500', '#8A2BE2', '#00CED1']

# Variables globales (estado)
current_year = datetime.now().year
circuit = "Monaco"
year = current_year
session_type = "Qualifying"
session_types = ["Qualifying", "Race"]
session = None
driver_options = []
selected_driver = ""
fig = None
fig_sectors = None
fig_laptimes = None
efficiency_score = 0.0
coast_percentage = 0.0

# Cache de datos de sesión (se calculan una vez al cargar sesión)
session_cache = {
    'driver_colors': {},
    'circuit_info': None
}


def load_session_data(circuit_name: str, sess_type: str, yr: int):
    """Carga una sesión de F1"""
    try:
        sess = fastf1.get_session(yr, circuit_name, sess_type)
        sess.load()
        return sess
    except Exception as e:
        print(f"Error cargando {sess_type}: {e}")
        return None


def get_driver_options_list(sess):
    """Retorna lista de opciones de pilotos"""
    if sess is None:
        return []
    options = []
    for driver in sess.drivers:
        try:
            data = sess.get_driver(driver)
            options.append(f"{data['Abbreviation']} - {data['FullName']}")
        except:
            options.append(f"{driver} - Driver {driver}")
    return options


def get_driver_number(sess, display_name: str):
    """Obtiene el número de piloto desde el display name"""
    if sess is None:
        return None
    for driver in sess.drivers:
        try:
            data = sess.get_driver(driver)
            if f"{data['Abbreviation']} - {data['FullName']}" == display_name:
                return driver
        except:
            if f"{driver} - Driver {driver}" == display_name:
                return driver
    return None


def get_driver_data(sess, driver, cache):
    """Obtiene todos los datos del piloto de una sola vez para evitar llamadas repetidas a la API"""
    if sess is None or not driver:
        return None

    try:
        # Datos básicos del piloto
        driver_info = sess.get_driver(driver)
        abbrev = driver_info['Abbreviation']
        color = cache['driver_colors'].get(
            driver) or cache['driver_colors'].get(abbrev) or FALLBACK_COLORS[0]

        # Todas las vueltas del piloto
        all_laps = sess.laps.pick_driver(driver)
        if all_laps is None or all_laps.empty:
            return None

        # Vuelta más rápida y su telemetría
        fastest_lap = all_laps.pick_fastest()
        fastest_telemetry = None
        if fastest_lap is not None and not fastest_lap.empty:
            try:
                fastest_telemetry = fastest_lap.get_telemetry()
            except:
                pass

        # Vueltas rápidas (quicklaps)
        quick_laps = all_laps.pick_quicklaps()

        return {
            'abbrev': abbrev,
            'color': color,
            'all_laps': all_laps,
            'fastest_lap': fastest_lap,
            'fastest_telemetry': fastest_telemetry,
            'quick_laps': quick_laps,
            'circuit_info': cache['circuit_info']
        }
    except Exception as e:
        print(f"Error obteniendo datos del piloto: {e}")
        return None


def plot_telemetry_combined(driver_data):
    """Gráfico combinado de Speed, Throttle/Brake, RPM y Gear con eje X compartido"""
    if driver_data is None:
        return None, 0.0

    telemetry = driver_data['fastest_telemetry']
    if telemetry is None or telemetry.empty:
        return None, 0.0

    abbrev = driver_data['abbrev']
    color = driver_data['color']
    circuit_info = driver_data['circuit_info']

    # Detectar zonas de coast/lift: pendiente negativa de throttle, throttle < 95% y freno no aplicado
    telemetry['ThrottleSlope'] = telemetry['Throttle'].diff().fillna(0)
    telemetry['Coast'] = (
        (telemetry['ThrottleSlope'] < 0) &
        (telemetry['Throttle'] < 95) &
        (telemetry['Brake'] == 0)
    )
    coast_pct = round((telemetry['Coast'].sum() / len(telemetry)) * 100, 1)
    coast_mask = telemetry['Coast']

    # Crear 4 subplots con eje X compartido
    fig_plot = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(
            "Speed (orange = Coast/Lift)",
            "Throttle & Brake",
            "RPM",
            "Gear"
        ),
        row_heights=[0.3, 0.25, 0.25, 0.2]
    )

    # Fila 1: Velocidad
    fig_plot.add_trace(go.Scatter(
        x=telemetry['Distance'], y=telemetry['Speed'],
        mode='lines', name=f"{abbrev} - Speed",
        line=dict(color=color, width=2)
    ), row=1, col=1)

    if coast_mask.any():
        fig_plot.add_trace(go.Scatter(
            x=telemetry.loc[coast_mask, 'Distance'],
            y=telemetry.loc[coast_mask, 'Speed'],
            mode='markers', name='Coast/Lift',
            marker=dict(color='#FFA500', size=4, opacity=0.7)
        ), row=1, col=1)

    # Fila 2: Throttle y Brake
    fig_plot.add_trace(go.Scatter(
        x=telemetry['Distance'], y=telemetry['Throttle'],
        mode='lines', name=f"{abbrev} - Throttle",
        line=dict(color='#00FF00', width=2)
    ), row=2, col=1)

    fig_plot.add_trace(go.Scatter(
        x=telemetry['Distance'], y=telemetry['Brake'] * 100,
        mode='lines', name=f"{abbrev} - Brake",
        line=dict(color='#FF0000', width=2)
    ), row=2, col=1)

    if coast_mask.any():
        fig_plot.add_trace(go.Scatter(
            x=telemetry.loc[coast_mask, 'Distance'],
            y=telemetry.loc[coast_mask, 'Throttle'],
            mode='markers', name='Coast Points',
            marker=dict(color='#FFA500', size=4, opacity=0.7),
            showlegend=False
        ), row=2, col=1)

    fig_plot.add_hline(y=95, line_dash="dash", line_color="yellow",
                       opacity=0.5, row=2, col=1)

    # Fila 3: RPM
    fig_plot.add_trace(go.Scatter(
        x=telemetry['Distance'], y=telemetry['RPM'],
        mode='lines', name=f"{abbrev} - RPM",
        line=dict(color=color, width=2)
    ), row=3, col=1)

    # Fila 4: Gear
    fig_plot.add_trace(go.Scatter(
        x=telemetry['Distance'], y=telemetry['nGear'],
        mode='lines', name=f"{abbrev} - Gear",
        line=dict(color='#FFD700', width=2, shape='hv'),
        fill='tozeroy', fillcolor='rgba(255, 215, 0, 0.3)'
    ), row=4, col=1)

    # Añadir curvas del circuito a todos los subplots
    if circuit_info is not None and hasattr(circuit_info, 'corners') and circuit_info.corners is not None:
        for corner in circuit_info.corners.itertuples():
            if hasattr(corner, 'Distance') and hasattr(corner, 'Number'):
                for row in [1, 2, 3, 4]:
                    fig_plot.add_vline(
                        x=corner.Distance, line_dash="dash", line_color="gray",
                        opacity=0.4, row=row, col=1)

    fig_plot.update_layout(
        title=f"Telemetría Completa - {abbrev} - Vuelta más rápida",
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom",
                    y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=50, t=100, b=50),
        height=900
    )

    fig_plot.update_yaxes(title_text="km/h", row=1, col=1)
    fig_plot.update_yaxes(title_text="%", row=2, col=1)
    fig_plot.update_yaxes(title_text="RPM", row=3, col=1)
    fig_plot.update_yaxes(title_text="Gear", row=4, col=1, dtick=1)
    fig_plot.update_xaxes(title_text="Distancia (m)", row=4, col=1)

    return fig_plot, coast_pct


def plot_sector_times(driver_data):
    """Gráfico de barras con tiempos por sector de todas las vueltas válidas"""
    if driver_data is None:
        return None

    quick_laps = driver_data['quick_laps']
    if quick_laps is None or quick_laps.empty:
        return None

    abbrev = driver_data['abbrev']

    valid_laps = quick_laps.dropna(
        subset=['Sector1Time', 'Sector2Time', 'Sector3Time'])
    if valid_laps.empty:
        return None

    s1_times = [t.total_seconds() for t in valid_laps['Sector1Time']]
    s2_times = [t.total_seconds() for t in valid_laps['Sector2Time']]
    s3_times = [t.total_seconds() for t in valid_laps['Sector3Time']]
    lap_numbers = valid_laps['LapNumber'].astype(int).tolist()

    fig_plot = go.Figure()
    fig_plot.add_trace(go.Bar(name='Sector 1', x=lap_numbers,
                       y=s1_times, marker_color='#FF6B6B'))
    fig_plot.add_trace(go.Bar(name='Sector 2', x=lap_numbers,
                       y=s2_times, marker_color='#4ECDC4'))
    fig_plot.add_trace(go.Bar(name='Sector 3', x=lap_numbers,
                       y=s3_times, marker_color='#45B7D1'))

    fig_plot.update_layout(
        title=f"Tiempos por Sector - {abbrev}",
        xaxis_title="Vuelta",
        yaxis_title="Tiempo (s)",
        barmode='group',
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom",
                    y=1.02, xanchor="right", x=1),
        height=400
    )
    return fig_plot


def plot_laptime_evolution(driver_data):
    """Gráfico de línea con evolución de tiempos por vuelta"""
    if driver_data is None:
        return None

    all_laps = driver_data['all_laps']
    if all_laps is None or all_laps.empty:
        return None

    abbrev = driver_data['abbrev']
    color = driver_data['color']

    valid_laps = all_laps.dropna(subset=['LapTime'])
    if valid_laps.empty:
        return None

    lap_times = [t.total_seconds() for t in valid_laps['LapTime']]
    lap_numbers = valid_laps['LapNumber'].astype(int).tolist()

    fastest_idx = lap_times.index(min(lap_times))
    colors = [color if i !=
              fastest_idx else '#FFD700' for i in range(len(lap_times))]
    sizes = [8 if i != fastest_idx else 14 for i in range(len(lap_times))]

    fig_plot = go.Figure()
    fig_plot.add_trace(go.Scatter(
        x=lap_numbers, y=lap_times,
        mode='lines+markers',
        name=abbrev,
        line=dict(color=color, width=2),
        marker=dict(color=colors, size=sizes)
    ))

    avg_time = sum(lap_times) / len(lap_times)
    fig_plot.add_hline(y=avg_time, line_dash="dash", line_color="gray",
                       annotation_text=f"Promedio: {avg_time:.3f}s")

    fig_plot.update_layout(
        title=f"Evolución de Tiempos - {abbrev} (⭐ = vuelta rápida)",
        xaxis_title="Vuelta",
        yaxis_title="Tiempo (s)",
        template="plotly_dark",
        height=400
    )
    return fig_plot


def calculate_efficiency_score(driver_data):
    """Calcula el porcentaje promedio de tiempo a full throttle (>95%) usando telemetría de vuelta rápida"""
    if driver_data is None:
        return 0.0

    telemetry = driver_data['fastest_telemetry']
    if telemetry is None or telemetry.empty or 'Throttle' not in telemetry.columns:
        return 0.0

    total_samples = len(telemetry)
    full_throttle_samples = (telemetry['Throttle'] >= 95).sum()

    return round((full_throttle_samples / total_samples) * 100, 1)


def on_load_data(state):
    """Callback para cargar datos"""
    notify(state, "info",
           f"Cargando {state.session_type} de {state.circuit} {state.year}...")
    state.session = load_session_data(
        state.circuit, state.session_type, state.year)

    if state.session:
        # Inicializar cache de sesión (se hace UNA sola vez al cargar)
        try:
            session_cache['driver_colors'] = fastf1.plotting.get_driver_color_mapping(
                session=state.session)
        except:
            session_cache['driver_colors'] = {}

        try:
            session_cache['circuit_info'] = state.session.get_circuit_info()
        except:
            session_cache['circuit_info'] = None

        state.driver_options = get_driver_options_list(state.session)
        state.selected_driver = state.driver_options[0] if state.driver_options else ""
        update_chart(state)
        notify(state, "success",
               f"✅ {state.session_type} cargado correctamente")
    else:
        session_cache['driver_colors'] = {}
        session_cache['circuit_info'] = None
        state.driver_options = []
        state.selected_driver = ""
        state.fig = None
        state.fig_sectors = None
        state.fig_laptimes = None
        state.efficiency_score = 0.0
        state.coast_percentage = 0.0
        notify(state, "error", f"❌ Error cargando {state.session_type}")


def on_driver_change(state):
    """Callback cuando cambian los pilotos seleccionados"""
    update_chart(state)


def update_chart(state):
    """Actualiza todos los gráficos y KPIs usando datos precalculados"""
    if state.session and state.selected_driver:
        driver = get_driver_number(state.session, state.selected_driver)
        if driver:
            # Obtener TODOS los datos del piloto de una sola vez
            driver_data = get_driver_data(state.session, driver, session_cache)

            if driver_data:
                state.fig, state.coast_percentage = plot_telemetry_combined(
                    driver_data)
                state.fig_sectors = plot_sector_times(driver_data)
                state.fig_laptimes = plot_laptime_evolution(driver_data)
                state.efficiency_score = calculate_efficiency_score(
                    driver_data)
            else:
                state.fig = None
                state.fig_sectors = None
                state.fig_laptimes = None
                state.efficiency_score = 0.0
                state.coast_percentage = 0.0
        else:
            state.fig = None
            state.fig_sectors = None
            state.fig_laptimes = None
            state.efficiency_score = 0.0
            state.coast_percentage = 0.0
    else:
        state.fig = None
        state.fig_sectors = None
        state.fig_laptimes = None
        state.efficiency_score = 0.0
        state.coast_percentage = 0.0


# Definir la página
with tgb.Page() as page:
    tgb.text("# 🏎️ F1 Speed Trace Dashboard", mode="md")
    tgb.text("---", mode="md")

    # Inputs en una sola línea
    with tgb.layout(columns="2 1 2 1"):
        tgb.input("{circuit}", label="Circuito")
        tgb.number("{year}", label="Año", min=2018, max=current_year)
        tgb.selector("{session_type}", lov="{session_types}",
                     dropdown=True, label="Sesión")
        tgb.button("🔄 Cargar Datos", on_action=on_load_data)

    tgb.text("---", mode="md")

    # Selector de piloto
    with tgb.part(render="{len(driver_options) > 0}"):
        tgb.text("### Seleccionar piloto:", mode="md")
        tgb.selector("{selected_driver}", lov="{driver_options}", dropdown=True,
                     on_change=on_driver_change, width="100%")

    # KPIs de Rendimiento
    with tgb.part(render="{efficiency_score > 0}"):
        tgb.text("### 📊 KPIs de Rendimiento", mode="md")
        with tgb.layout(columns="1 1"):
            tgb.text(
                "**Efficiency Score (% Full Throttle):** {efficiency_score}%", mode="md")
            tgb.text(
                "**Coast/Lift (% tiempo sin acelerador ni freno):** {coast_percentage}%", mode="md")

    # Gráfico combinado de telemetría (Speed, Throttle/Brake, RPM, Gear)
    with tgb.part(render="{fig is not None}"):
        tgb.chart(figure="{fig}")

    # Gráficos de Sector Times y Lap Evolution lado a lado
    with tgb.part(render="{fig_sectors is not None and fig_laptimes is not None}"):
        tgb.text("---", mode="md")
        with tgb.layout(columns="1 1"):
            tgb.chart(figure="{fig_sectors}")
            tgb.chart(figure="{fig_laptimes}")

    # Mensaje inicial
    with tgb.part(render="{session is None}"):
        tgb.text(
            "👆 Ingresa el circuito, año y tipo de sesión, luego presiona **Cargar Datos**", mode="md")


if __name__ == "__main__":
    Gui(page=page).run(title="F1 Speed Trace", dark_mode=True,
                       use_reloader=False, port=5001)
