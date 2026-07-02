import re
import math
import streamlit as st
import pandas as pd

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
        self.is_female = title in ["WGM", "WIM", "WFM", "WCM"]

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

dp_table = {
    100: 800, 99: 677, 98: 589, 97: 538, 96: 501, 95: 470, 94: 444, 93: 422, 92: 401, 91: 383,
    90: 366, 89: 351, 88: 336, 87: 322, 86: 309, 85: 296, 84: 284, 83: 273, 82: 262, 81: 251,
    80: 240, 79: 230, 78: 220, 77: 211, 76: 202, 75: 193, 74: 184, 73: 175, 72: 166, 71: 158,
    70: 149, 69: 141, 68: 133, 67: 125, 66: 117, 65: 110, 64: 102, 63: 95, 62: 87, 61: 80,
    60: 72,  59: 65,  58: 57,  57: 50,  56: 43,  55: 36,  54: 29,  53: 21,  52: 14,  51: 7,
    50: 0,
    49: -7,  48: -14, 47: -21, 46: -29, 45: -36, 44: -43, 43: -50, 42: -57, 41: -65, 40: -72,
    39: -80, 38: -87, 37: -95, 36: -102, 35: -110, 34: -117, 33: -125, 32: -133, 31: -141, 30: -149,
    29: -158, 28: -166, 27: -175, 26: -184, 25: -193, 24: -202, 23: -211, 22: -220, 21: -230, 20: -240,
    19: -251, 18: -262, 17: -273, 16: -284, 15: -296, 14: -309, 13: -322, 12: -336, 11: -351, 10: -366,
    9: -383,  8: -401,  7: -422,  6: -444,  5: -470,  4: -501,  3: -538,  2: -589,  1: -677,  0: -800
}

# =========================================================
# LÓGICA DE CÁLCULO FIDE
# =========================================================
# MODIFICADO: Acepta una lista 'hypothetical_opps' en lugar de 'last_opp'
def evaluate_norm(norm_p, norm_type, players, hypothetical_opps=None, tournament_exemption=False):
    if norm_type == "GM":
        target_rank, elo_threshold, elo_target, target_performance = 6, 2200, 2380, 2599.5
    elif norm_type == "IM":
        target_rank, elo_threshold, elo_target, target_performance = 5, 2050, 2230, 2449.5
    elif norm_type == "WGM":
        target_rank, elo_threshold, elo_target, target_performance = 4, 2000, 2180, 2399.5
    elif norm_type == "WIM":
        target_rank, elo_threshold, elo_target, target_performance = 3, 1850, 2030, 2249.5
    else:
        return None

    opponent_elos = []
    valid_titles_total = 0
    category_titles = 0
    federation_counts = {}
    same_fed_as_player = 0
    actual_score = 0.0
    opponent_details = []

    for m in norm_p.matches:
        if m.opponent > 0 and m.color != "F" and not m.special:
            opp = get_player(m.opponent, players)
            if opp:
                opponent_elos.append(opp.elo)
                rank = get_title_rank(opp.title)
                if rank > 0:
                    valid_titles_total += 1
                    if rank >= target_rank:
                        category_titles += 1
                        
                federation_counts[opp.federation] = federation_counts.get(opp.federation, 0) + 1
                if opp.federation == norm_p.federation:
                    same_fed_as_player += 1
                
                res_str = "0"
                if m.result == "+":
                    actual_score += 1.0
                    res_str = "1"
                elif m.result == "=":
                    actual_score += 0.5
                    res_str = "0.5"
                    
                opponent_details.append({
                    "Rk": opp.id, "Nombre": opp.name, "ELO": opp.elo, 
                    "Título": opp.title if opp.title else "-", "Fed": opp.federation, "Resultado": res_str
                })

    # Itera sobre los oponentes hipotéticos si los hay
    if hypothetical_opps:
        for opp in hypothetical_opps:
            if opp:
                opponent_elos.append(opp.elo)
                rank = get_title_rank(opp.title)
                if rank > 0:
                    valid_titles_total += 1
                    if rank >= target_rank:
                        category_titles += 1
                        
                federation_counts[opp.federation] = federation_counts.get(opp.federation, 0) + 1
                if opp.federation == norm_p.federation:
                    same_fed_as_player += 1

                opponent_details.append({
                    "Rk": opp.id, "Nombre": opp.name, "ELO": opp.elo, 
                    "Título": opp.title if opp.title else "-", "Fed": opp.federation, "Resultado": "?"
                })

    n = len(opponent_elos)
    if n == 0:
        return None

    elo_adjusted = False
    original_min_elo = 0
    min_elo = min(opponent_elos)
    
    if min_elo < elo_threshold:
        min_idx = opponent_elos.index(min_elo)
        original_min_elo = min_elo
        opponent_elos[min_idx] = elo_threshold
        elo_adjusted = True

    avg_elo = sum(opponent_elos) / n
    max_freq = max(federation_counts.values()) if federation_counts else 0

    actual_p = actual_score / n if n > 0 else 0
    actual_p_idx = max(0, min(100, int(round(actual_p * 100.0))))
    actual_dp = dp_table.get(actual_p_idx, 0)
    actual_performance = round(avg_elo + actual_dp + 1e-9)

    min_required_score = -1.0
    s = 0.0
    while s <= n:
        p = s / n
        p_idx = max(0, min(100, int(round(p * 100.0))))
        dp = dp_table.get(p_idx, 0)
        if avg_elo + dp >= target_performance:
            min_required_score = s
            break
        s += 0.5

    req_cat_min = max(3, math.ceil(n / 3.0))
    req_tot_min = math.ceil(n / 2.0)
    req_fed_player_max = math.floor(n * 3.0 / 5.0)
    req_fed_any_max = math.floor(n * 2.0 / 3.0)
    req_fed_diff_min = 1 if tournament_exemption else 3

    cond_elo = avg_elo >= elo_target
    cond_cat_titles = category_titles >= req_cat_min
    cond_tot_titles = valid_titles_total >= req_tot_min
    cond_fed_player = same_fed_as_player <= req_fed_player_max
    cond_fed_any = max_freq <= req_fed_any_max
    cond_fed_diff = len(federation_counts) >= req_fed_diff_min
    cond_score = (min_required_score >= 0.0 and actual_score >= min_required_score)

    norm_achieved = cond_score and cond_elo and cond_cat_titles and cond_tot_titles and cond_fed_player and cond_fed_any and cond_fed_diff

    return {
        "norm_achieved": norm_achieved, "n_games": n, "opponent_details": opponent_details,
        "avg_elo": avg_elo, "actual_score": actual_score, "actual_performance": actual_performance,
        "min_required_score": min_required_score, "target_performance": target_performance, "elo_target": elo_target,
        "category_titles": category_titles, "req_cat_min": req_cat_min, "cond_cat_titles": cond_cat_titles,
        "valid_titles_total": valid_titles_total, "req_tot_min": req_tot_min, "cond_tot_titles": cond_tot_titles,
        "same_fed_as_player": same_fed_as_player, "req_fed_player_max": req_fed_player_max, "cond_fed_player": cond_fed_player,
        "max_freq": max_freq, "req_fed_any_max": req_fed_any_max, "cond_fed_any": cond_fed_any,
        "num_feds": len(federation_counts), "req_fed_diff_min": req_fed_diff_min, "cond_fed_diff": cond_fed_diff,
        "cond_elo": cond_elo, "cond_score": cond_score, "elo_adjusted": elo_adjusted,
        "original_min_elo": original_min_elo, "elo_threshold": elo_threshold
    }

def scan_all_players_for_norms(players_list, include_womens_titles=True, tournament_exemption=False):
    successful_candidates = []
    title_hierarchy = {"GM": 4, "IM": 3, "WGM": 2, "WIM": 1, "": 0, "FM": 0, "WFM": 0, "CM": 0, "WCM": 0}
    
    for p in players_list:
        valid_matches = [m for m in p.matches if m.opponent > 0 and m.color != "F" and not m.special]
        if len(valid_matches) < 8: 
            continue
            
        player_title_level = title_hierarchy.get(p.title, 0)
        norms_to_test = []
        
        if player_title_level < 4: norms_to_test.append("GM")
        if player_title_level < 3: norms_to_test.append("IM")
        
        if include_womens_titles and p.is_female:
            if player_title_level < 2: norms_to_test.append("WGM")
            if player_title_level < 1: norms_to_test.append("WIM")
        
        for norm_type in norms_to_test:
            res = evaluate_norm(p, norm_type, players_list, tournament_exemption=tournament_exemption)
            if res and res["norm_achieved"]:
                successful_candidates.append({
                    "Rk": p.id,
                    "Jugador": p.name,
                    "Fed": p.federation,
                    "Norma": norm_type,
                    "Ptos": res["actual_score"],
                    "Performance": res["actual_performance"],
                    "ARO": round(res["avg_elo"], 1)
                })
                
    return successful_candidates


# --- FUNCIÓN A FALTA DE 1 RONDA ---
def get_candidate_requirements(norm_p, norm_type, players, tournament_exemption=False):
    if norm_type == "GM":
        target_rank, elo_threshold, elo_target, target_performance = 6, 2200, 2380, 2599.5
    elif norm_type == "IM":
        target_rank, elo_threshold, elo_target, target_performance = 5, 2050, 2230, 2449.5
    elif norm_type == "WGM":
        target_rank, elo_threshold, elo_target, target_performance = 4, 2000, 2180, 2399.5
    elif norm_type == "WIM":
        target_rank, elo_threshold, elo_target, target_performance = 3, 1850, 2030, 2249.5
    else: return None

    opponent_elos = []
    valid_titles_total = 0
    category_titles = 0
    federation_counts = {}
    same_fed_as_player = 0
    actual_score = 0.0

    for m in norm_p.matches:
        if m.opponent > 0 and m.color != "F" and not m.special:
            opp = get_player(m.opponent, players)
            if opp:
                opponent_elos.append(opp.elo)
                rank = get_title_rank(opp.title)
                if rank > 0:
                    valid_titles_total += 1
                    if rank >= target_rank:
                        category_titles += 1
                federation_counts[opp.federation] = federation_counts.get(opp.federation, 0) + 1
                if opp.federation == norm_p.federation:
                    same_fed_as_player += 1
                if m.result == "+": actual_score += 1.0
                elif m.result == "=": actual_score += 0.5

    n_current = len(opponent_elos)
    if n_current == 0: return None
    n_target = n_current + 1

    req_cat_min = max(3, math.ceil(n_target / 3.0))
    req_tot_min = math.ceil(n_target / 2.0)
    req_fed_player_max = math.floor(n_target * 3.0 / 5.0)
    req_fed_any_max = math.floor(n_target * 2.0 / 3.0)
    req_fed_diff_min = 1 if tournament_exemption else 3

    missing_cat = max(0, req_cat_min - category_titles)
    missing_tot = max(0, req_tot_min - valid_titles_total)
    
    if missing_cat > 1 or missing_tot > 1: return None 
    if same_fed_as_player > req_fed_player_max: return None
        
    max_freq_current = max(federation_counts.values()) if federation_counts else 0
    if max_freq_current > req_fed_any_max: return None

    req_title = "-"
    if missing_cat == 1: req_title = f"Tit. {norm_type}+"
    elif missing_tot == 1: req_title = "Tit. Cualquiera"

    req_fed = "-"
    forbidden_feds = []
    
    if same_fed_as_player == req_fed_player_max:
        forbidden_feds.append(norm_p.federation)
        
    for fed, count in federation_counts.items():
        if count == req_fed_any_max:
            if fed not in forbidden_feds:
                forbidden_feds.append(fed)

    if len(federation_counts) < req_fed_diff_min - 1: return None
    elif len(federation_counts) == req_fed_diff_min - 1: req_fed = "Fed. Nueva"
    elif forbidden_feds:
        if norm_p.federation in forbidden_feds and len(forbidden_feds) == 1: req_fed = "Extranjero"
        else: req_fed = f"Evitar: {', '.join(forbidden_feds)}"

    def get_min_elo_for_score(res):
        target_score = actual_score + res
        p_val = target_score / n_target
        p_idx = max(0, min(100, int(round(p_val * 100.0))))
        dp = dp_table.get(p_idx, 0)
        
        for test_elo in range(1400, 2850):
            elos = opponent_elos.copy()
            elos.append(test_elo)
            
            min_elo_val = min(elos)
            if min_elo_val < elo_threshold:
                min_idx = elos.index(min_elo_val)
                elos[min_idx] = elo_threshold
                
            avg = sum(elos) / n_target
            perf = round(avg + dp + 1e-9)
            
            if avg >= elo_target and perf >= target_performance: return test_elo
        return None

    min_elo_win = get_min_elo_for_score(1.0)
    min_elo_draw = get_min_elo_for_score(0.5)
    min_elo_loss = get_min_elo_for_score(0.0)

    if min_elo_win is None: return None

    result_needs = []
    if min_elo_loss is not None: result_needs.append(f"1D (ELO ≥ {min_elo_loss})")
    if min_elo_draw is not None: result_needs.append(f"1T (ELO ≥ {min_elo_draw})")
    if min_elo_win is not None: result_needs.append(f"1V (ELO ≥ {min_elo_win})")

    if not result_needs: return None

    return {
        "Rk": norm_p.id,
        "Jugador": norm_p.name,
        "Ptos": actual_score,
        "Norma": norm_type,
        "Resultado necesario": " // ".join(result_needs),
        "Títulos req.": req_title,
        "Banderas req.": req_fed
    }

# --- FUNCIÓN A FALTA DE 2 RONDAS ---
def get_candidate_requirements_2_rounds(norm_p, norm_type, players, tournament_exemption=False):
    if norm_type == "GM":
        target_rank, elo_threshold, elo_target, target_performance = 6, 2200, 2380, 2599.5
    elif norm_type == "IM":
        target_rank, elo_threshold, elo_target, target_performance = 5, 2050, 2230, 2449.5
    elif norm_type == "WGM":
        target_rank, elo_threshold, elo_target, target_performance = 4, 2000, 2180, 2399.5
    elif norm_type == "WIM":
        target_rank, elo_threshold, elo_target, target_performance = 3, 1850, 2030, 2249.5
    else: return None

    opponent_elos = []
    valid_titles_total = 0
    category_titles = 0
    federation_counts = {}
    same_fed_as_player = 0
    actual_score = 0.0

    for m in norm_p.matches:
        if m.opponent > 0 and m.color != "F" and not m.special:
            opp = get_player(m.opponent, players)
            if opp:
                opponent_elos.append(opp.elo)
                rank = get_title_rank(opp.title)
                if rank > 0:
                    valid_titles_total += 1
                    if rank >= target_rank:
                        category_titles += 1
                federation_counts[opp.federation] = federation_counts.get(opp.federation, 0) + 1
                if opp.federation == norm_p.federation:
                    same_fed_as_player += 1
                if m.result == "+": actual_score += 1.0
                elif m.result == "=": actual_score += 0.5

    n_current = len(opponent_elos)
    if n_current == 0: return None
    n_target = n_current + 2

    req_cat_min = max(3, math.ceil(n_target / 3.0))
    req_tot_min = math.ceil(n_target / 2.0)
    req_fed_player_max = math.floor(n_target * 3.0 / 5.0)
    req_fed_any_max = math.floor(n_target * 2.0 / 3.0)
    req_fed_diff_min = 1 if tournament_exemption else 3

    missing_cat = max(0, req_cat_min - category_titles)
    missing_tot = max(0, req_tot_min - valid_titles_total)
    
    if missing_cat > 2 or missing_tot > 2: return None 

    # Determinación de los títulos requeridos combinados
    req_title_list = []
    c = missing_cat
    t = missing_tot
    if c == 2: req_title_list.append(f"2x Tit. {norm_type}+")
    elif c == 1:
        req_title_list.append(f"1x Tit. {norm_type}+")
        if t >= 2: req_title_list.append("1x Tit. Cualquiera")
    elif c == 0:
        if t == 2: req_title_list.append("2x Tit. Cualquiera")
        elif t == 1: req_title_list.append("1x Tit. Cualquiera")
    req_title = " + ".join(req_title_list) if req_title_list else "-"

    # Determinación de las banderas requeridas combinadas
    forbidden_feds_any = []
    forbidden_feds_both = []

    if same_fed_as_player + 1 > req_fed_player_max: forbidden_feds_any.append(norm_p.federation)
    elif same_fed_as_player + 2 > req_fed_player_max: forbidden_feds_both.append(norm_p.federation)

    for fed, count in federation_counts.items():
        if count + 1 > req_fed_any_max and fed not in forbidden_feds_any:
            forbidden_feds_any.append(fed)
        elif count + 2 > req_fed_any_max and fed not in forbidden_feds_both and fed not in forbidden_feds_any:
            forbidden_feds_both.append(fed)

    req_fed_parts = []
    if len(federation_counts) < req_fed_diff_min - 2: return None
    elif len(federation_counts) == req_fed_diff_min - 2: req_fed_parts.append("2 Feds. Nuevas")
    elif len(federation_counts) == req_fed_diff_min - 1: req_fed_parts.append("1 Fed. Nueva")

    if forbidden_feds_any: req_fed_parts.append(f"Evitar: {','.join(forbidden_feds_any)}")
    if forbidden_feds_both: req_fed_parts.append(f"Máx 1 de: {','.join(forbidden_feds_both)}")
    
    req_fed = " | ".join(req_fed_parts) if req_fed_parts else "-"

    # Busca la media de ELO necesaria para los 2 siguientes oponentes
    def get_min_avg_elo_for_score(res):
        target_score = actual_score + res
        p_val = target_score / n_target
        p_idx = max(0, min(100, int(round(p_val * 100.0))))
        dp = dp_table.get(p_idx, 0)
        
        for test_avg_elo in range(1400, 2850):
            elos = opponent_elos.copy()
            elos.append(test_avg_elo)
            elos.append(test_avg_elo)
            
            min_elo_val = min(elos)
            if min_elo_val < elo_threshold:
                min_idx = elos.index(min_elo_val)
                elos[min_idx] = elo_threshold
                
            avg = sum(elos) / n_target
            perf = round(avg + dp + 1e-9)
            
            if avg >= elo_target and perf >= target_performance: return test_avg_elo
        return None

    scenarios = [
        (0.0, "2D"), (0.5, "1T+1D"), (1.0, "1V+1D/2T"), (1.5, "1V+1T"), (2.0, "2V")
    ]

    result_needs = []
    for pts, label in scenarios:
        min_elo = get_min_avg_elo_for_score(pts)
        if min_elo is not None:
            result_needs.append(f"{label} (Med. ELO ≥ {min_elo})")

    if not result_needs: return None

    return {
        "Rk": norm_p.id,
        "Jugador": norm_p.name,
        "Ptos": actual_score,
        "Norma": norm_type,
        "Resultado necesario": " // ".join(result_needs),
        "Títulos req.": req_title,
        "Banderas req.": req_fed
    }


def scan_candidates_for_norms(players_list, include_womens_titles=True, tournament_exemption=False, rounds_to_go=1):
    candidates = []
    title_hierarchy = {"GM": 4, "IM": 3, "WGM": 2, "WIM": 1, "": 0, "FM": 0, "WFM": 0, "CM": 0, "WCM": 0}
    
    for p in players_list:
        valid_matches = [m for m in p.matches if m.opponent > 0 and m.color != "F" and not m.special]
        
        # Filtramos a los que no tienen suficientes rondas según la estimación
        if len(valid_matches) < (9 - rounds_to_go): continue
            
        player_title_level = title_hierarchy.get(p.title, 0)
        norms_to_test = []
        if player_title_level < 4: norms_to_test.append("GM")
        if player_title_level < 3: norms_to_test.append("IM")
        
        if include_womens_titles and p.is_female:
            if player_title_level < 2: norms_to_test.append("WGM")
            if player_title_level < 1: norms_to_test.append("WIM")
            
        for norm_type in norms_to_test:
            if rounds_to_go == 1:
                reqs = get_candidate_requirements(p, norm_type, players_list, tournament_exemption=tournament_exemption)
            else:
                reqs = get_candidate_requirements_2_rounds(p, norm_type, players_list, tournament_exemption=tournament_exemption)
                
            if reqs:
                candidates.append(reqs)
                
    return candidates

# =========================================================
# INTERFAZ WEB (STREAMLIT)
# =========================================================
st.set_page_config(page_title="Calculadora de Normas FIDE", page_icon="♟️", layout="centered")

st.title("♟️ Calculadora de Normas FIDE")
st.subheader("Creado por el Árbitro FIDE Juan Antonio Márquez León (22237364)")
st.write("Esta herramienta analiza el cuadro cruzado de un torneo suizo para verificar normas obtenidas o proyectar candidatos antes de la última ronda.")

uploaded_file = st.file_uploader("Sube aquí el archivo 'crosstable.txt' generado por el programa de emparejamientos (Vega):", type=["txt"])

if uploaded_file is not None:
    players = []
    
    try:
        content = uploaded_file.read().decode("utf-8")
    except UnicodeDecodeError:
        content = uploaded_file.read().decode("ISO-8859-1")
        
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
    
    # -----------------------------------------------------
    # GESTIÓN FEMENINA Y EXCEPCIONES 
    # -----------------------------------------------------
    st.markdown("---")
    st.write("### 👩 Gestión de Categoría Femenina")
    st.write("El sistema ha detectado automáticamente a las jugadoras con títulos femeninos (WGM, WIM, WFM, WCM). Puedes buscar y añadir manualmente a jugadoras sin título o con título absoluto para que puedan ser evaluadas para normas WGM/WIM.")
    
    player_options_dict = {p.id: f"{p.id} - {p.name} (ELO: {p.elo})" for p in players}
    preselected_females = [p.id for p in players if p.is_female]
    
    selected_female_ids = st.multiselect(
        "Selecciona las jugadoras femeninas del torneo:",
        options=list(player_options_dict.keys()),
        default=preselected_females,
        format_func=lambda x: player_options_dict[x]
    )
    
    for p in players:
        p.is_female = (p.id in selected_female_ids)
    
    st.markdown("---")
    st.write("### 🌍 Configuración y Normativa del Torneo")
    
    all_feds = [p.federation for p in players]
    inferred_host_fed = max(set(all_feds), key=all_feds.count) if all_feds else ""
    
    host_fed = st.text_input("Federación organizadora (Host Federation):", value=inferred_host_fed, max_chars=3)
    
    foreign_rated_players = [p for p in players if p.federation != host_fed and p.elo > 0]
    foreign_feds = set(p.federation for p in foreign_rated_players)
    wim_plus_titles = {"GM", "IM", "WGM", "WIM"}
    titled_foreign_count = sum(1 for p in foreign_rated_players if p.title in wim_plus_titles)
    
    tournament_exemption = (len(foreign_rated_players) >= 20 and len(foreign_feds) >= 3 and titled_foreign_count >= 10)
    
    if tournament_exemption:
        st.success(f"✅ **Excepción FIDE 1.4.3d aplicable:** Hay {len(foreign_rated_players)} extranjeros con ELO, de {len(foreign_feds)} federaciones, y {titled_foreign_count} con título WIM+. **Se ignora el requisito de haber jugado contra 3 federaciones.**")
    else:
        st.info(f"ℹ️ **Excepción FIDE 1.4.3d NO aplicable:** El torneo cuenta con {len(foreign_rated_players)} extranjeros con ELO (mín. 20), de {len(foreign_feds)} federaciones (mín. 3), y {titled_foreign_count} con título WIM+ (mín. 10).")

    st.markdown("---")
    
    tab_individual, tab_escaner, tab_candidatos = st.tabs([
        "🔍 Búsqueda Individual", 
        "🚀 Normas Cumplidas", 
        "🔮 Estimación Próximas Rondas"
    ])

# -----------------------------------------------------
    # PESTAÑA 1: MODO INDIVIDUAL (AJUSTADA)
    # -----------------------------------------------------
    with tab_individual:
        player_options = {p.id: f"{p.id} - {p.name} (ELO: {p.elo})" for p in players}
        
        norm_player_id = st.selectbox("Selecciona el jugador que busca la norma:", options=list(player_options.keys()), format_func=lambda x: player_options[x])
        norm_p = get_player(norm_player_id, players)

        available_norms = ["GM", "IM"]
        if norm_p and norm_p.is_female:
            available_norms.extend(["WGM", "WIM"])

        norm_type = st.radio("¿Qué tipo de norma deseas evaluar?", available_norms, horizontal=True)

        # MODIFICADO: Uso de botones (radio) para seleccionar rivales extra
        num_hypothetical = st.radio("¿Añadir rivales hipotéticos extra para cálculos?", [0, 1, 2], horizontal=True)
        
        hypothetical_opps = []
        if num_hypothetical >= 1:
            opp1_id = st.selectbox("Selecciona el 1º rival adicional:", options=list(player_options.keys()), format_func=lambda x: player_options[x], key="rival_1")
            hypothetical_opps.append(get_player(opp1_id, players))
            
        if num_hypothetical == 2:
            opp2_id = st.selectbox("Selecciona el 2º rival adicional:", options=list(player_options.keys()), format_func=lambda x: player_options[x], key="rival_2")
            hypothetical_opps.append(get_player(opp2_id, players))

        if norm_p:
            res = evaluate_norm(norm_p, norm_type, players, hypothetical_opps, tournament_exemption)
            
            if res is None:
                st.error("El jugador seleccionado no posee partidas válidas computables.")
            else:
                # ... (El resto de la lógica de visualización del informe permanece igual)
                def st_status(met):
                    return "✅ CUMPLIDO" if met else "❌ NO CUMPLIDO"

                st.markdown("---")
                st.header(f"Informe de requisitos: Norma de {norm_type}")
                st.subheader(f"Jugador: {norm_p.name} ({norm_p.federation})")
                
                st.write("### 📋 Listado de rivales")
                st.table(res["opponent_details"])
                
                if res["elo_adjusted"]:
                    st.warning(f"⚠️ **Umbral FIDE aplicado:** El rival con menor ELO ({res['original_min_elo']}) ha sido ajustado a {res['elo_threshold']} para el cálculo del ELO medio.")

                st.write("### 📊 Verificación de condiciones FIDE")
                st.write(f"**1. ELO medio de los rivales** (Mínimo: {res['elo_target']})  \n*Actual:* **{res['avg_elo']:.2f}** ➔ {st_status(res['cond_elo'])}")
                st.write(f"**2. Rivales titulados categoría {norm_type}+** (Mínimo: {res['req_cat_min']})  \n*Actual:* **{res['category_titles']}** ➔ {st_status(res['cond_cat_titles'])}")
                st.write(f"**3. Rivales titulados totales** (Mínimo: {res['req_tot_min']})  \n*Actual:* **{res['valid_titles_total']}** ➔ {st_status(res['cond_tot_titles'])}")
                st.write(f"**4. Rivales de la misma federación ({norm_p.federation})** (Máximo: {res['req_fed_player_max']})  \n*Actual:* **{res['same_fed_as_player']}** ➔ {st_status(res['cond_fed_player'])}")
                st.write(f"**5. Rivales de la federación más común** (Máximo: {res['req_fed_any_max']})  \n*Actual:* **{res['max_freq']}** ➔ {st_status(res['cond_fed_any'])}")
                
                if tournament_exemption:
                    st.write(f"**6. Federaciones diferentes** (Excepción torneo internacional aplicada)  \n*Actual:* **{res['num_feds']}** ➔ ✅ CUMPLIDO")
                else:
                    st.write(f"**6. Federaciones diferentes** (Mínimo: {res['req_fed_diff_min']})  \n*Actual:* **{res['num_feds']}** ➔ {st_status(res['cond_fed_diff'])}")
                
                if res["min_required_score"] < 0.0:
                    st.error(f"**7. Puntuación mínima** (Para TPR {res['target_performance']}) ➔ **❌ IMPOSIBLE** (La media de ELO es demasiado baja)")
                else:
                    st.write(f"**7. Puntuación mínima necesaria** (Para TPR {res['target_performance']}) (Requiere: {res['min_required_score']} ptos)  \n*Performance actual:* **{res['actual_performance']}**  \n*Puntuación actual:* **{res['actual_score']} ptos** ➔ {st_status(res['cond_score'])}")
                    
                    if res["norm_achieved"]:
                        st.balloons()
                        st.success(f"🎉 ¡El jugador cumple TODOS los requisitos para optar a la norma de {norm_type}!")
                    else:
                        st.info("💡 Revisa las condiciones marcadas con '❌' para ver qué falla en la norma.")

    # -----------------------------------------------------
    # PESTAÑA 2: ESCÁNER DEL TORNEO (NORMAS CONSEGUIDAS)
    # -----------------------------------------------------
    with tab_escaner:
        st.write("### 🤖 Búsqueda automática de normas (Cumplidas)")
        st.write("Analiza el torneo completo y encuentra a los jugadores que **ya han logrado normas** con los resultados actuales.")
        
        modo_escaner = st.radio(
            "Selecciona el tipo de análisis:",
            ["Análisis Completo (GM, IM, WGM, WIM)", "Solo Títulos Absolutos (GM, IM)"],
            horizontal=True,
            key="radio_cumplidas"
        )
        
        incluir_femeninos = (modo_escaner == "Análisis Completo (GM, IM, WGM, WIM)")
        
        if st.button("Buscar normas cumplidas", type="primary"):
            with st.spinner('Analizando cuadro cruzado...'):
                candidates = scan_all_players_for_norms(players, include_womens_titles=incluir_femeninos, tournament_exemption=tournament_exemption)
                
            if len(candidates) > 0:
                st.success(f"¡Se han detectado {len(candidates)} normas cumplidas!")
                df = pd.DataFrame(candidates)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.warning("No se ha detectado ninguna norma completada en este torneo.")

    # -----------------------------------------------------
    # PESTAÑA 3: ESTIMACIÓN PRÓXIMAS RONDAS (CANDIDATOS)
    # -----------------------------------------------------
    with tab_candidatos:
        st.write("### 🔮 Candidatos a norma")
        st.write("Identifica a los jugadores que aún no tienen norma, pero que **podrían conseguirla** sumando los resultados de las próximas rondas (útil antes de los últimos emparejamientos).")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            modo_escaner_cand = st.radio(
                "Selecciona el tipo de análisis:",
                ["Análisis Completo (GM, IM, WGM, WIM)", "Solo Títulos Absolutos (GM, IM)"],
                horizontal=True,
                key="radio_candidatos"
            )
            
        with col2:
            rondas_restantes = st.radio(
                "¿Cuántas rondas quedan?",
                [1, 2],
                format_func=lambda x: f"A falta de {x} ronda(s)"
            )
            
        incluir_femeninos_cand = (modo_escaner_cand == "Análisis Completo (GM, IM, WGM, WIM)")
        
        if st.button("Buscar candidatos", type="primary"):
            with st.spinner(f'Proyectando escenarios a falta de {rondas_restantes} ronda(s)...'):
                future_candidates = scan_candidates_for_norms(
                    players, 
                    include_womens_titles=incluir_femeninos_cand, 
                    tournament_exemption=tournament_exemption, 
                    rounds_to_go=rondas_restantes
                )
                
            if len(future_candidates) > 0:
                st.info(f"Se han encontrado {len(future_candidates)} jugadores con opciones matemáticas a falta de {rondas_restantes} ronda(s).")
                df_future = pd.DataFrame(future_candidates)
                st.dataframe(df_future, use_container_width=True, hide_index=True)
            else:
                st.warning(f"Ningún jugador sin norma actual tiene opciones matemáticas de alcanzarla jugando {rondas_restantes} ronda(s) más.")
