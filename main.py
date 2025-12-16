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


def plot_telemetry_combined(sess, driver):
    """Gráfico combinado de velocidad, acelerador y freno con ejes X compartidos"""
    if sess is None or not driver:
        return None

    try:
        driver_colors = fastf1.plotting.get_driver_color_mapping(session=sess)
    except:
        driver_colors = {}

    laps = sess.laps.pick_driver(driver).pick_fastest()
    if laps is None or laps.empty:
        return None
    try:
        telemetry = laps.get_telemetry()
        if telemetry.empty:
            return None
        abbrev = sess.get_driver(driver)['Abbreviation']
        color = driver_colors.get(driver) or driver_colors.get(
            abbrev) or FALLBACK_COLORS[0]
    except:
        return None

    # Crear subplots con eje X compartido
    fig_plot = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=("Speed Trace", "Throttle & Brake Trace"),
        row_heights=[0.5, 0.5]
    )

    # Velocidad (fila 1)
    fig_plot.add_trace(go.Scatter(
        x=telemetry['Distance'],
        y=telemetry['Speed'],
        mode='lines',
        name=f"{abbrev} - Speed",
        line=dict(color=color, width=2)
    ), row=1, col=1)

    # Acelerador (fila 2 - verde)
    fig_plot.add_trace(go.Scatter(
        x=telemetry['Distance'],
        y=telemetry['Throttle'],
        mode='lines',
        name=f"{abbrev} - Throttle",
        line=dict(color='#00FF00', width=2)
    ), row=2, col=1)

    # Freno (fila 2 - rojo)
    fig_plot.add_trace(go.Scatter(
        x=telemetry['Distance'],
        y=telemetry['Brake'] * 100,
        mode='lines',
        name=f"{abbrev} - Brake",
        line=dict(color='#FF0000', width=2)
    ), row=2, col=1)

    # Añadir curvas del circuito a ambos subplots
    try:
        circuit_info = sess.get_circuit_info()
        if hasattr(circuit_info, 'corners') and circuit_info.corners is not None:
            for corner in circuit_info.corners.itertuples():
                if hasattr(corner, 'Distance') and hasattr(corner, 'Number'):
                    for row in [1, 2]:
                        fig_plot.add_vline(
                            x=corner.Distance, line_dash="dash", line_color="gray",
                            opacity=0.5, row=row, col=1)
    except:
        pass

    fig_plot.update_layout(
        title=f"Telemetría - {abbrev} - Vuelta más rápida",
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom",
                    y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=50, t=100, b=50),
        height=700
    )

    fig_plot.update_yaxes(title_text="Velocidad (km/h)", row=1, col=1)
    fig_plot.update_yaxes(title_text="Porcentaje (%)", row=2, col=1)
    fig_plot.update_xaxes(title_text="Distancia (m)", row=2, col=1)

    return fig_plot


def on_load_data(state):
    """Callback para cargar datos"""
    notify(state, "info",
           f"Cargando {state.session_type} de {state.circuit} {state.year}...")
    state.session = load_session_data(
        state.circuit, state.session_type, state.year)

    if state.session:
        state.driver_options = get_driver_options_list(state.session)
        state.selected_driver = state.driver_options[0] if state.driver_options else ""
        update_chart(state)
        notify(state, "success",
               f"✅ {state.session_type} cargado correctamente")
    else:
        state.driver_options = []
        state.selected_driver = ""
        state.fig = None
        notify(state, "error", f"❌ Error cargando {state.session_type}")


def on_driver_change(state):
    """Callback cuando cambian los pilotos seleccionados"""
    update_chart(state)


def update_chart(state):
    """Actualiza el gráfico combinado"""
    if state.session and state.selected_driver:
        driver = get_driver_number(state.session, state.selected_driver)
        if driver:
            state.fig = plot_telemetry_combined(state.session, driver)
        else:
            state.fig = None
    else:
        state.fig = None


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

    # Gráfico combinado de telemetría
    with tgb.part(render="{fig is not None}"):
        tgb.chart(figure="{fig}")

    # Mensaje inicial
    with tgb.part(render="{session is None}"):
        tgb.text(
            "👆 Ingresa el circuito, año y tipo de sesión, luego presiona **Cargar Datos**", mode="md")


if __name__ == "__main__":
    Gui(page=page).run(title="F1 Speed Trace", dark_mode=True,
                       use_reloader=False, port=5001)
