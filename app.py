import re
import math
import streamlit as st

# =========================================================
# CONFIGURACIÓN DE LA ESTRUCTURA INTERNA
# =========================================================
class Match:
    def __init__(self, raw_token, result="", color="", opponent=0, special="", is_valid=False):
        self.raw_token = raw_token
        self.result = result
        self.color = color
        self.opponent = opponent
        self.special = special
        self.is_valid = is_valid

class Player:
    def __init__(self, id, name, elo, title, federation):
        self.id = id
        self.name = name
        self.elo = elo
        self.title = title
        self.federation = federation
        self.matches = []

def get_title_rank(title):
    ranks = {"GM": 6, "IM": 5, "WGM": 4, "WIM": 3, "FM": 2, "WFM": 1}
    return ranks.get(title, 0)

def parse_match_token(t):
    m = Match(raw_token=t)
    match = re.match(r"^([+=-]?)([WBF])(\d+)$|^([+=-]?)(HPB|FPB)$|^(--)$", t)
    
    if match:
        m.is_valid = True
        if match.group(6):
            m.special = "--"
        elif match.group(5):
            m.result = match.group(4) if match.group(4) else ""
            m.special = match.group(5)
        elif match.group(3):
            m.result = match.group(1) if match.group(1) else ""
            m.color = match.group(2)
            m.opponent = int(match.group(3))
            
    return m

def get_player(player_id, players):
    for p in players:
        if p.id == player_id:
            return p
    return None

# Tabla p-dp integrada (Conversión oficial FIDE)
dp_table = {
    100: 800, 99: 677, 98: 589, 97: 538, 96: 501, 95: 470, 94: 444, 93: 422, 92: 401, 91: 383,
    90: 366, 89: 351, 88: 336, 87: 322, 86: 309, 85: 296, 84: 284, 83: 273, 82: 262, 81: 251,
    80: 240, 79: 230, 78: 220, 77: 211, 76: 202, 75: 193, 74: 184, 73: 175, 72: 166, 71: 158,
    70: 149, 69: 141, 68: 133, 67: 125, 66: 117, 65: 110, 64: 102, 63: 95, 62: 87, 61: 80,
    60: 72,  59: 65,  58: 57,  57: 50,  56: 43,  55: 36,  54: 29,  53: 21,  52: 14,  51: 7,
    50: 0,
    49: -7,  48: -14, 47: -21, 46: -29, 45: -36, 44: -43, 43: -50, 42: -57, 41: -65, 40: -72,
    39: -80, 38: -87, 37: -95, 36: -102,35: -110,34: -117,33: -125,32: -133,31: -141,30: -149,
    29: -158,28: -166,27: -175,26: -184,25: -193,24: -202,23: -211,22: -220,21: -230,20: -240,
    19: -251,18: -262,17: -273,16: -284,15: -296,14: -309,13: -322,12: -336,11: -351,10: -366,
    9: -383,  8: -401,  7: -422,  6: -444,  5: -470,  4: -501,  3: -538,  2: -589,  1: -677,  0: -800
}

# =========================================================
# INTERFAZ WEB (STREAMLIT)
# =========================================================
st.set_page_config(page_title="Calculadora de Normas FIDE", page_icon="♟️", layout="centered")

st.title("♟️ Calculadora de Normas FIDE")
st.subheader("Creado por el Árbitro FIDE Juan Antonio Márquez León (22237364)")

st.write("Esta herramienta analiza el cuadro cruzado de un torneo suizo para verificar si un jugador cumple las condiciones para obtener una norma. Incluye la opción de simular la última partida del torneo para verificar el resultado necesario para obtener la norma.")

# 1. Subida del archivo por el usuario
uploaded_file = st.file_uploader("Sube aquí el archivo 'crosstable.txt' generado por el programa de emparejamientos (Vega):", type=["txt"])

if uploaded_file is not None:
    players = []
    
    # Procesar el archivo subido en memoria
    content = uploaded_file.read().decode("utf-8")
    lines = content.splitlines()
    
    player_re = re.compile(r"^\s*(\d+)\s+(.+?)\s+(\d+)\s+(?:([A-Z]{2,3})\s+)?([A-Z]{3})\s+[0-9.]+\s*\|")
    
    for line in lines:
        match = player_re.search(line)
        if match:
            p_id = int(match.group(1))
            name = match.group(2).strip()
            elo = int(match.group(3))
            title = match.group(4).strip() if match.group(4) else ""
            federation = match.group(5).strip()
            
            p = Player(p_id, name, elo, title, federation)
            players.append(p)
        
        tokens = line.split()
        for token in tokens:
            m = parse_match_token(token)
            if m.is_valid and players:
                players[-1].matches.append(m)

    st.success("¡Archivo cargado correctamente!")

    # Crear listado de nombres bonitos para el buscador
    player_options = {p.id: f"{p.id} - {p.name} (ELO: {p.elo})" for p in players}
    
    st.markdown("---")
    st.subheader("Selección del jugador")
    
    # Selección de jugador principal
    norm_player_id = st.selectbox("Selecciona el jugador que busca la norma:", options=list(player_options.keys()), format_func=lambda x: player_options[x])
    norm_p = get_player(norm_player_id, players)

    # Selección del tipo de norma
    norm_type = st.radio("¿Qué tipo de norma deseas evaluar?", ["GM", "IM", "WGM", "WIM"], horizontal=True)

    # Rival manual opcional
    add_opp = st.checkbox("¿Deseas añadir un rival extra manualmente para cálculos hipotéticos?")
    last_opp = None
    if add_opp:
        last_opponent_id = st.selectbox("Selecciona el rival adicional:", options=list(player_options.keys()), format_func=lambda x: player_options[x], key="last_rival")
        last_opp = get_player(last_opponent_id, players)

    if norm_p:
        # Configurar los umbrales según la norma
        if norm_type == "GM":
            target_rank, elo_threshold, elo_target, target_performance = 6, 2200, 2380, 2599.5
        elif norm_type == "IM":
            target_rank, elo_threshold, elo_target, target_performance = 5, 2050, 2230, 2449.5
        elif norm_type == "WGM":
            target_rank, elo_threshold, elo_target, target_performance = 4, 2000, 2180, 2399.5
        elif norm_type == "WIM":
            target_rank, elo_threshold, elo_target, target_performance = 3, 1850, 2030, 2249.5

        opponent_elos = []
        titles = []
        valid_titles_total = 0
        category_titles = 0
        federation_counts = {}
        same_fed_as_player = 0
        actual_score = 0.0
        opponent_details = []

        # Extraer estadísticas de las partidas reales
        for m in norm_p.matches:
            if m.opponent > 0 and m.color != "F" and not m.special:
                opp = get_player(m.opponent, players)
                if opp:
                    # Datos directos del rival
                    opponent_elos.append(opp.elo)
                    titles.append(opp.title if opp.title else "Ninguno")
                    
                    rank = get_title_rank(opp.title)
                    if rank > 0:
                        valid_titles_total += 1
                        if rank >= target_rank:
                            category_titles += 1
                            
                    federation_counts[opp.federation] = federation_counts.get(opp.federation, 0) + 1
                    if opp.federation == norm_p.federation:
                        same_fed_as_player += 1
                    
                    # Resultado
                    res_str = "0"
                    if m.result == "+":
                        actual_score += 1.0
                        res_str = "1"
                    elif m.result == "=":
                        actual_score += 0.5
                        res_str = "0.5"
                        
                    opponent_details.append({
                        "ID": opp.id, "Nombre": opp.name, "ELO": opp.elo, 
                        "Título": opp.title if opp.title else "-", "Fed": opp.federation, "Resultado": res_str
                    })

        # Extraer estadísticas si hay rival hipotético añadido
        if last_opp:
            opponent_elos.append(last_opp.elo)
            titles.append(last_opp.title if last_opp.title else "Ninguno")
            
            rank = get_title_rank(last_opp.title)
            if rank > 0:
                valid_titles_total += 1
                if rank >= target_rank:
                    category_titles += 1
                    
            federation_counts[last_opp.federation] = federation_counts.get(last_opp.federation, 0) + 1
            if last_opp.federation == norm_p.federation:
                same_fed_as_player += 1

            opponent_details.append({
                "ID": last_opp.id, "Nombre": last_opp.name, "ELO": last_opp.elo, 
                "Título": last_opp.title if last_opp.title else "-", "Fed": last_opp.federation, "Resultado": "?"
            })

        n = len(opponent_elos)

        if n > 0:
            # Umbral FIDE (Floor limit)
            elo_adjusted = False
            original_min_elo = 0
            min_elo = min(opponent_elos)
            
            if min_elo < elo_threshold:
                min_idx = opponent_elos.index(min_elo)
                original_min_elo = min_elo
                opponent_elos[min_idx] = elo_threshold
                elo_adjusted = True

            # ELO Medio de los Rivales (Rc)
            avg_elo = sum(opponent_elos) / n
            max_freq = max(federation_counts.values()) if federation_counts else 0
            
            # 1. Calculo de la performance
            actual_p = actual_score / n
            actual_p_idx = int(round(actual_p * 100.0))
            actual_p_idx = max(0, min(100, actual_p_idx)) 
            actual_dp = dp_table.get(actual_p_idx, 0)
            actual_performance = round(avg_elo + actual_dp + 1e-9)
            
            # Cálculo de puntuación mínima
            min_required_score = -1.0
            s = 0.0
            while s <= n:
                p = s / n
                p_idx = int(round(p * 100.0))
                dp = dp_table.get(p_idx, 0)
                if avg_elo + dp >= target_performance:
                    min_required_score = s
                    break
                s += 0.5

            # Evaluación de condiciones FIDE
            req_cat_min = max(3, math.ceil(n / 3.0))
            req_tot_min = math.ceil(n / 2.0)
            req_fed_player_max = math.floor(n * 3.0 / 5.0)
            req_fed_any_max = math.floor(n * 2.0 / 3.0)

            cond_elo = avg_elo >= elo_target
            cond_cat_titles = category_titles >= req_cat_min
            cond_tot_titles = valid_titles_total >= req_tot_min
            cond_fed_player = same_fed_as_player <= req_fed_player_max
            cond_fed_any = max_freq <= req_fed_any_max
            cond_fed_diff = len(federation_counts) >= 3
            cond_score = (min_required_score >= 0.0 and actual_score >= min_required_score)

            def st_status(met):
                return "✅ CUMPLIDO" if met else "❌ NO CUMPLIDO"

            # ==========================================
            # MOSTRAR RESULTADOS EN LA PÁGINA
            # ==========================================
            st.markdown("---")
            st.header(f"Informe de requisitos para norma de {norm_type}")
            st.subheader(f"Jugador: {norm_p.name} ({norm_p.federation})")
            
            # Tabla de Oponentes
            st.write("### 📋 Listado de rivales")
            st.table(opponent_details)
            
            if elo_adjusted:
                st.warning(f"⚠️ **Umbral FIDE aplicado:** El rival con menor ELO ({original_min_elo}) ha sido ajustado a {elo_threshold} para el cálculo del ELO medio.")

            # Bloque de condiciones
            st.write("### 📊 Verificación de las condiciones de la FIDE")
            
            st.write(f"**1. ELO medio de los rivales** (Mínimo requerido: {elo_target})  \n*Actual:* **{avg_elo:.2f}** ➔ {st_status(cond_elo)}")
            st.write(f"**2. Rivales titulados de categoría {norm_type} o superior** (Mínimo requerido: {req_cat_min})  \n*Actual:* **{category_titles}** ➔ {st_status(cond_cat_titles)}")
            st.write(f"**3. Rivales titulados totales** (Mínimo requerido: {req_tot_min})  \n*Actual:* **{valid_titles_total}** ➔ {st_status(cond_tot_titles)}")
            st.write(f"**4. Rivales de la misma federación ({norm_p.federation})** (Máximo permitido: {req_fed_player_max})  \n*Actual:* **{same_fed_as_player}** ➔ {st_status(cond_fed_player)}")
            st.write(f"**5. Rivales de la federación más común** (Máximo permitido: {req_fed_any_max})  \n*Actual:* **{max_freq}** ➔ {st_status(cond_fed_any)}")
            st.write(f"**6. Número de federaciones diferentes** (Mínimo requerido: 3)  \n*Actual:* **{len(federation_counts)}** ➔ {st_status(cond_fed_diff)}")
            
            if min_required_score < 0.0:
                st.error(f"**7. Puntuación mínima necesaria** (Para TPR {target_performance}) ➔ **❌ IMPOSIBLE** (La media de ELO es demasiado baja; incluso ganando todo no se alcanza la performance)")
            else:
                st.write(f"**7. Puntuación mínima necesaria** (Para TPR {target_performance}) (Puntuación requerida: {min_required_score} ptos)  \n*Performance actual:* **{performance}**  \n*Puntuación actual:* **{actual_score} ptos** ➔ {st_status(cond_score)}")
                
                if cond_score and cond_elo and cond_cat_titles and cond_tot_titles and cond_fed_player and cond_fed_any and cond_fed_diff:
                    st.balloons()
                    st.success(f"🎉 ¡El jugador cumple TODOS los requisitos para optar a la norma de {norm_type}!")
                else:
                    st.info("💡 Revisa las condiciones marcadas con '❌' para ver qué falla en la norma.")
        else:
            st.error("El jugador seleccionado no posee partidas válidas computables en este archivo.")
