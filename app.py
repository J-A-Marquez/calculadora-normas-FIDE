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
def evaluate_norm(norm_p, norm_type, players, hypothetical_opps=None, hypothetical_score=0.0, tournament_exemption=False, national_final=False):
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
        
    actual_score += hypothetical_score
    original_opponent_elos = opponent_elos.copy()

    elo_adjusted = False
    original_min_elo = 0
    min_elo = min(opponent_elos)
    
    if min_elo < elo_threshold:
        min_idx = opponent_elos.index(min_elo)
        original_min_elo = min_elo
        opponent_elos[min_idx] = elo_threshold
        elo_adjusted = True

    avg_elo = sum(opponent_elos) / n
    unadjusted_avg_elo = sum(original_opponent_elos) / n
    max_freq = max(federation_counts.values()) if federation_counts else 0

    actual_p = actual_score / n if n > 0 else 0
    actual_p_idx = max(0, min(100, int(round(actual_p * 100.0))))
    actual_dp = dp_table.get(actual_p_idx, 0)
    
    actual_performance = round(avg_elo + actual_dp + 1e-9)
    unadjusted_performance = round(unadjusted_avg_elo + actual_dp + 1e-9)

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
    
    # EXCEPCIÓN: Campeonato Nacional
    if national_final:
        cond_fed_player = True
        cond_fed_any = True
        cond_fed_diff = True
    else:
        cond_fed_player = same_fed_as_player <= req_fed_player_max
        cond_fed_any = max_freq <= req_fed_any_max
        cond_fed_diff = len(federation_counts) >= req_fed_diff_min
        
    cond_score = (min_required_score >= 0.0 and actual_score >= min_required_score)

    norm_achieved = cond_score and cond_elo and cond_cat_titles and cond_tot_titles and cond_fed_player and cond_fed_any and cond_fed_diff

    return {
        "norm_achieved": norm_achieved, "n_games": n, "opponent_details": opponent_details,
        "avg_elo": avg_elo, "unadjusted_avg_elo": unadjusted_avg_elo,
        "actual_score": actual_score, 
        "actual_performance": actual_performance, "unadjusted_performance": unadjusted_performance,
        "min_required_score": min_required_score, "target_performance": target_performance, "elo_target": elo_target,
        "category_titles": category_titles, "req_cat_min": req_cat_min, "cond_cat_titles": cond_cat_titles,
        "valid_titles_total": valid_titles_total, "req_tot_min": req_tot_min, "cond_tot_titles": cond_tot_titles,
        "same_fed_as_player": same_fed_as_player, "req_fed_player_max": req_fed_player_max, "cond_fed_player": cond_fed_player,
        "max_freq": max_freq, "req_fed_any_max": req_fed_any_max
