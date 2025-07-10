from datetime import datetime
import streamlit as st
import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import seaborn as sns

# Configuración inicial
fastf1.plotting.setup_mpl(mpl_timedelta_support=True,
                          misc_mpl_mods=False, color_scheme='fastf1')


def load_session_data(circuit, session_type, year=2024):
    """Carga los datos de la sesión especificada"""
    try:
        session = fastf1.get_session(year, circuit, session_type)
        session.load()
        return session
    except Exception as e:
        st.error(f"Error cargando la sesión {session_type}: {str(e)}")
        return None


def load_weekend_data(circuit, year=2024):
    """Carga los datos de qualifying y carrera para el fin de semana"""
    with st.spinner("Cargando datos de FastF1..."):
        # Crear columnas de progreso
        progress_col1, progress_col2 = st.columns(2)

        with progress_col1:
            qualifying = load_session_data(circuit, "Qualifying", year)

        with progress_col2:
            race = load_session_data(circuit, "Race", year)

    return qualifying, race


def get_session_drivers_info(session):
    """Obtiene información de los pilotos de la sesión"""
    drivers_info = []
    for driver in session.drivers:
        try:
            driver_data = session.get_driver(driver)
            drivers_info.append({
                'number': driver,
                'abbreviation': driver_data['Abbreviation'],
                'full_name': driver_data['FullName']
            })
        except:
            drivers_info.append({
                'number': driver,
                'abbreviation': driver,
                'full_name': f"Driver {driver}"
            })
    return drivers_info


def plot_laptimes_distribution(session, selected_pilots, figsize=(15, 6)):
    """Gráfico de distribución de tiempos de vuelta para qualifying usando violinplot"""
    fig, ax = plt.subplots(figsize=figsize)

    # Obtener abreviaciones de pilotos
    pilot_abbreviations = []
    for pilot in selected_pilots:
        try:
            driver_info = session.get_driver(pilot)
            pilot_abbreviations.append(driver_info['Abbreviation'])
        except:
            pilot_abbreviations.append(pilot)

    # Preparar datos
    all_laps = []
    for pilot in selected_pilots:
        driver_laps = session.laps.pick_driver(pilot).pick_quicklaps()
        if not driver_laps.empty:
            driver_laps = driver_laps.copy()
            driver_laps["LapTime(s)"] = driver_laps["LapTime"].dt.total_seconds(
            )
            driver_laps["Driver"] = session.get_driver(pilot)['Abbreviation']
            all_laps.append(driver_laps)

    if not all_laps:
        ax.text(0.5, 0.5, 'No hay datos disponibles',
                ha='center', va='center', transform=ax.transAxes)
        return fig

    combined_laps = pd.concat(all_laps, ignore_index=True)

    # Violinplot usando colores de FastF1
    try:
        palette = fastf1.plotting.get_driver_color_mapping(session=session)
    except:
        palette = None

    sns.violinplot(data=combined_laps,
                   x="Driver",
                   y="LapTime(s)",
                   hue="Driver",
                   inner=None,
                   density_norm="area",
                   order=pilot_abbreviations,
                   palette=palette,
                   ax=ax)

    # Swarmplot si hay datos de compuesto
    if 'Compound' in combined_laps.columns:
        try:
            sns.swarmplot(data=combined_laps,
                          x="Driver",
                          y="LapTime(s)",
                          order=pilot_abbreviations,
                          hue="Compound",
                          palette=fastf1.plotting.get_compound_mapping(
                              session=session),
                          linewidth=0,
                          size=4,
                          ax=ax)
        except:
            pass

    ax.set_xlabel('Piloto')
    ax.set_ylabel('Tiempo de vuelta (s)')
    sns.despine(left=True, bottom=True)
    plt.tight_layout()

    return fig


def plot_speed_trace(session, selected_pilots, figsize=(15, 6)):
    """Gráfico de velocidad a lo largo de la pista con anotaciones"""
    fig, ax = plt.subplots(figsize=figsize)

    # Usar colores de FastF1
    try:
        driver_colors = fastf1.plotting.get_driver_color_mapping(
            session=session)
    except:
        driver_colors = {}

    for i, driver in enumerate(selected_pilots):
        driver_laps = session.laps.pick_driver(driver).pick_fastest()
        if driver_laps is not None and not driver_laps.empty:
            try:
                telemetry = driver_laps.get_telemetry()
                driver_abbrev = session.get_driver(driver)['Abbreviation']

                # Usar color de FastF1 o color por defecto
                driver_color = driver_colors.get(
                    driver) or driver_colors.get(driver_abbrev)
                if not driver_color:
                    # Colores de respaldo si FastF1 no tiene el mapeo
                    fallback_colors = ['#0600EF', '#FF8700', '#FF1801', '#DC143C', '#00D2BE',
                                       '#FF69B4', '#32CD32', '#FF4500', '#8A2BE2', '#00CED1']
                    driver_color = fallback_colors[i % len(fallback_colors)]

                if not telemetry.empty:
                    ax.plot(telemetry['Distance'], telemetry['Speed'],
                            color=driver_color,
                            label=driver_abbrev, linewidth=2)
            except Exception as e:
                print(f"Error con piloto {driver}: {e}")
                continue

    # Añadir información del circuito si está disponible
    try:
        circuit_info = session.get_circuit_info()
        if hasattr(circuit_info, 'corners') and circuit_info.corners is not None:
            for corner in circuit_info.corners.itertuples():
                if hasattr(corner, 'Distance') and hasattr(corner, 'Number'):
                    ax.axvline(x=corner.Distance, color='gray',
                               linestyle='--', alpha=0.5)
                    ax.text(corner.Distance, ax.get_ylim()[1]*0.95, f'T{corner.Number}',
                            rotation=90, ha='right', va='top', fontsize=8)
    except:
        pass

    ax.set_xlabel('Distancia (m)')
    ax.set_ylabel('Velocidad (km/h)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    return fig


def plot_position_changes(session, figsize=(15, 6)):
    """Gráfico de cambios de posición durante la carrera"""
    fig, ax = plt.subplots(figsize=figsize)

    # Para cada piloto, obtener su abreviación y plotear posición
    len_drivers = len(session.drivers)
    for drv in session.drivers:
        drv_laps = session.laps.pick_drivers(drv)

        abb = drv_laps['Driver'].iloc[0]
        style = fastf1.plotting.get_driver_style(identifier=abb,
                                                 style=['color', 'linestyle'],
                                                 session=session)

        ax.plot(drv_laps['LapNumber'], drv_laps['Position'],
                label=abb, **style)

    # Configurar ejes
    ax.set_ylim([len_drivers + 0.5, 0.5])
    ax.set_yticks([i for i in range(1, len_drivers + 1)])
    ax.set_xlabel('Lap')
    ax.set_ylabel('Position')

    # Leyenda fuera del área de ploteo
    ax.legend(bbox_to_anchor=(1.0, 1.02))

    return fig


def plot_strategy(session, figsize=(15, 6)):
    """Gráfico de estrategias de neumáticos"""
    fig, ax = plt.subplots(figsize=figsize)

    # Usar mapeo de colores de FastF1 para compuestos
    try:
        compound_colors = fastf1.plotting.get_compound_mapping(session=session)
    except:
        compound_colors = {
            'SOFT': '#da020e',
            'MEDIUM': '#ffd12e',
            'HARD': '#f0f0ec',
            'INTERMEDIATE': '#43b02a',
            'WET': '#0067ad'
        }

    laps = session.laps
    drivers = session.drivers

    # Obtener abreviaciones
    driver_abbreviations = []
    for driver in drivers:
        try:
            driver_abbrev = session.get_driver(driver)['Abbreviation']
            driver_abbreviations.append(driver_abbrev)
        except:
            driver_abbreviations.append(driver)

    for i, driver in enumerate(drivers):
        driver_laps = laps.pick_driver(driver)
        if driver_laps.empty:
            continue

        stints = driver_laps.groupby(['Stint', 'Compound']).agg({
            'LapNumber': ['min', 'max'],
            'Compound': 'first'
        }).reset_index()

        for _, stint in stints.iterrows():
            start_lap = stint[('LapNumber', 'min')]
            end_lap = stint[('LapNumber', 'max')]
            compound = stint[('Compound', 'first')]

            color = compound_colors.get(compound, '#808080')
            ax.barh(i, end_lap - start_lap + 1, left=start_lap-1,
                    color=color, edgecolor='black', linewidth=0.5)

    # Configurar ejes
    ax.set_xlabel('Número de vuelta')
    ax.set_ylabel('Piloto')
    ax.set_yticks(range(len(drivers)))
    ax.set_yticklabels(driver_abbreviations)

    # Leyenda
    legend_elements = [mpatches.Patch(color=color, label=compound)
                       for compound, color in compound_colors.items()]
    ax.legend(handles=legend_elements, loc='upper right')
    ax.grid(True, alpha=0.3)

    return fig


def plot_team_pace_ranking(session, figsize=(15, 6)):
    """Gráfico de ranking de equipos por tiempo medio de vuelta"""
    laps = session.laps.pick_quicklaps()
    transformed_laps = laps.copy()

    transformed_laps.loc[:, "LapTime (s)"] = laps["LapTime"].dt.total_seconds()

    # order the team from the fastest (lowest median lap time) tp slower
    team_order = (
        transformed_laps[["Team", "LapTime (s)"]]
        .groupby("Team")
        .median()["LapTime (s)"]
        .sort_values()
        .index
    )

    # make a color palette associating team names to hex codes
    team_palette = {team: fastf1.plotting.get_team_color(team, session=session)
                    for team in team_order}

    fig, ax = plt.subplots(figsize=figsize)
    sns.boxplot(
        data=transformed_laps,
        x="Team",
        y="LapTime (s)",
        hue="Team",
        order=team_order,
        palette=team_palette,
        whiskerprops=dict(color="white"),
        boxprops=dict(edgecolor="white"),
        medianprops=dict(color="grey"),
        capprops=dict(color="white"),
    )

    ax.grid(visible=False)
    ax.set(xlabel=None)

    return fig


def main():
    st.set_page_config(page_title="Dashboard Formula 1", layout="wide")

    st.title("🏎️ Dashboard Formula 1")
    st.markdown("Análisis de datos de carreras y clasificaciones usando FastF1")
    present_year = int(datetime.now().strftime("%Y"))

    # Sidebar para inputs
    with st.sidebar:
        st.header("Configuración")

        # Input del circuito
        circuit = st.text_input(
            "Circuito",
            placeholder="Ej: Monaco, Spain, Brazil",
            help="Nombre del circuito en inglés"
        )

        # Año (opcional)
        year = st.number_input("Año", min_value=2018,
                               max_value=present_year, value=present_year)

        # Botón para cargar datos
        load_data = st.button("🔄 Cargar Datos", type="primary")

    # Estado de las sesiones
    if 'qualifying_session' not in st.session_state:
        st.session_state.qualifying_session = None
    if 'race_session' not in st.session_state:
        st.session_state.race_session = None

    # Cargar datos cuando se presiona el botón
    if load_data and circuit:
        qualifying, race = load_weekend_data(circuit, year)
        st.session_state.qualifying_session = qualifying
        st.session_state.race_session = race

        # Mostrar estado de carga
        status_messages = []
        if qualifying:
            status_messages.append("✅ Qualifying cargado")
        else:
            status_messages.append("❌ Error cargando Qualifying")

        if race:
            status_messages.append("✅ Race cargado")
        else:
            status_messages.append("❌ Error cargando Race")

        st.success(" | ".join(status_messages))

    # Mostrar gráficos usando tabs
    if st.session_state.qualifying_session or st.session_state.race_session:
        qualifying_session = st.session_state.qualifying_session
        race_session = st.session_state.race_session

        # Crear tabs
        tab1, tab2 = st.tabs(["🏁 Qualifying", "🏎️ Race"])

        with tab1:
            if qualifying_session:
                st.header("📊 Análisis de Qualifying")

                # Obtener información de pilotos de la sesión
                drivers_info = get_session_drivers_info(qualifying_session)

                # Crear opciones para el selector (mostrar abreviación y nombre completo)
                driver_options = []
                driver_mapping = {}
                for driver_info in drivers_info:
                    display_name = f"{driver_info['abbreviation']} - {driver_info['full_name']}"
                    driver_options.append(display_name)
                    driver_mapping[display_name] = driver_info['number']

                # Selector de pilotos
                selected_pilots_display = st.multiselect(
                    "Seleccionar pilotos para comparar:",
                    driver_options,
                    default=driver_options[:3] if len(
                        driver_options) >= 3 else driver_options,
                    max_selections=8,
                    help="Puedes seleccionar hasta 8 pilotos para comparar",
                    key="qualifying_pilots"
                )

                # Convertir display names a números de piloto
                selected_pilots = [driver_mapping[display]
                                   for display in selected_pilots_display]

                if selected_pilots:
                    st.subheader("Distribución de tiempos")
                    try:
                        fig1 = plot_laptimes_distribution(
                            qualifying_session, selected_pilots, figsize=(15, 10))
                        st.pyplot(fig1)
                        plt.close(fig1)
                    except Exception as e:
                        st.error(
                            f"Error generando gráfico de distribución: {str(e)}")

                    st.subheader("Velocidad en pista")
                    try:
                        fig2 = plot_speed_trace(
                            qualifying_session, selected_pilots, figsize=(15, 10))
                        st.pyplot(fig2)
                        plt.close(fig2)
                    except Exception as e:
                        st.error(
                            f"Error generando gráfico de velocidad: {str(e)}")
                else:
                    st.info(
                        "👆 Selecciona pilotos para ver los análisis de qualifying")
            else:
                st.warning("⚠️ No se pudieron cargar los datos de Qualifying")

        with tab2:
            if race_session:
                st.header("🏁 Análisis de Carrera")

                st.subheader("Cambios de posición")
                try:
                    fig3 = plot_position_changes(
                        race_session, figsize=(15, 10))
                    st.pyplot(fig3)
                    plt.close(fig3)
                except Exception as e:
                    st.error(
                        f"Error generando gráfico de posiciones: {str(e)}")

                st.subheader("Estrategias de neumáticos")
                try:
                    fig4 = plot_strategy(race_session, figsize=(15, 10))
                    st.pyplot(fig4)
                    plt.close(fig4)
                except Exception as e:
                    st.error(
                        f"Error generando gráfico de estrategia: {str(e)}")

                st.subheader("Ritmo por equipos")
                try:
                    fig5 = plot_team_pace_ranking(
                        race_session, figsize=(15, 10))
                    st.pyplot(fig5)
                    plt.close(fig5)
                except Exception as e:
                    st.error(
                        f"Error generando gráfico de ritmo por equipos: {str(e)}")
            else:
                st.warning("⚠️ No se pudieron cargar los datos de Race")

    elif circuit and load_data:
        st.warning(
            "⚠️ No se pudieron cargar los datos. Verifica el nombre del circuito.")

    else:
        st.info("👆 Configura el circuito y el año en el panel lateral para comenzar")

        # Información de ayuda
        with st.expander("ℹ️ Información de uso"):
            st.markdown("""
            **Nombres de circuitos válidos:**
            - Monaco, Spain, Brazil, United States, Japan, Australia, etc.
            - Usa nombres en inglés
            
            **Análisis disponibles:**
            - **Qualifying**: Distribución de tiempos y velocidad en pista
            - **Race**: Cambios de posición, estrategias de neumáticos y ritmo por equipos
            """)


if __name__ == "__main__":
    main()
