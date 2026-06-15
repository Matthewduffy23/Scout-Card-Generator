# player_card_app.py — Scouting Card Generator
# Replicates Canva scouting card design programmatically
# Canvas: 1920x1080px | Font: Montserrat | Background: #0a0f1c

import io, re, math, unicodedata, base64
from pathlib import Path
from datetime import date

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patheffects as pe
import requests
from PIL import Image

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Scouting Card Generator", layout="wide")

# ── Google Fonts ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&display=swap');
html, body, [class*="css"] { font-family: 'Montserrat', sans-serif !important; }
.stApp { background: #0a0f1c !important; color: #fff !important; }
section[data-testid="stSidebar"] { background: #060a14 !important; border-right: 1px solid #1a2540 !important; }
section[data-testid="stSidebar"] * { color: #fff !important; }
.stSelectbox > div > div { background: #0d1424 !important; border: 1px solid #1e2d4a !important; }
div[data-baseweb="select"] * { background: #0d1424 !important; color: #fff !important; }
div[data-baseweb="popover"] * { background: #0d1424 !important; color: #fff !important; }
.stTextInput > div > div > input, .stTextArea textarea {
    background: #0d1424 !important; border: 1px solid #1e2d4a !important; color: #fff !important;
}
.stButton > button {
    background: #fff !important; color: #000 !important; font-weight: 700 !important;
    font-family: 'Montserrat', sans-serif !important; border: none !important; border-radius: 4px !important;
}
label { color: #9ca3af !important; font-size: 11px !important; letter-spacing: .1em !important; text-transform: uppercase !important; }
h1, h2, h3 { color: #fff !important; font-family: 'Montserrat', sans-serif !important; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
BG          = "#0a0f1c"
ACCENT_PINK = "#ff66c4"
TREND_CYAN  = "#00cadc"
LABEL_COL   = "#e8eef8"
SUB_COL     = "#b8c0cf"
BAR_TRACK   = "#1a2540"
TAB_RED     = np.array([199, 54,  60],  dtype=float)  # #C7363C
TAB_GOLD    = np.array([240, 197, 106], dtype=float)  # #F0C56A
TAB_GREEN   = np.array([61,  166, 91],  dtype=float)  # #3DA65B

# Feature F metrics per position
FEATURE_F_METRICS = {
    "CF": {
        "Attacking":   ["Crosses per 90","Accurate crosses, %","Non-penalty goals per 90","xG per 90",
                        "Goal conversion, %","Head goals per 90","xA per 90","Progressive runs per 90",
                        "Shots per 90","Shots on target, %","Touches in box per 90"],
        "Defensive":   ["Aerial duels per 90","Aerial duels won, %","Defensive duels per 90",
                        "Defensive duels won, %","PAdj Interceptions"],
        "Possession":  ["Deep completions per 90","Dribbles per 90","Successful dribbles, %",
                        "Key passes per 90","Passes per 90","Accurate passes, %",
                        "Passes to penalty area per 90","Smart passes per 90"],
    },
    "CB": {
        "Attacking":   ["Non-penalty goals per 90","xG per 90","Offensive duels per 90","Offensive duels won, %","Progressive runs per 90"],
        "Defensive":   ["Aerial duels per 90","Aerial duels won, %","Defensive duels per 90",
                        "Defensive duels won, %","PAdj Interceptions","Shots blocked per 90"],
        "Possession":  ["Passes per 90","Accurate passes, %","Forward passes per 90",
                        "Accurate forward passes, %","Progressive passes per 90",
                        "Accurate progressive passes, %","Long passes per 90","Accurate long passes, %"],
    },
    "FB": {
        "Attacking":   ["Crosses per 90","Accurate crosses, %","Non-penalty goals per 90","xG per 90",
                        "xA per 90","Offensive duels per 90","Offensive duels won, %",
                        "Progressive runs per 90","Shots per 90","Shots on target, %","Touches in box per 90"],
        "Defensive":   ["Aerial duels per 90","Aerial duels won, %","Defensive duels per 90",
                        "Defensive duels won, %","Shots blocked per 90","PAdj Interceptions"],
        "Possession":  ["Deep completions per 90","Dribbles per 90","Successful dribbles, %",
                        "Forward passes per 90","Long passes per 90","Key passes per 90",
                        "Passes per 90","Accurate passes, %","Passes to final third per 90",
                        "Passes to penalty area per 90","Progressive passes per 90","Smart passes per 90"],
    },
    "CM": {
        "Attacking":   ["Crosses per 90","Non-penalty goals per 90","xG per 90","xA per 90",
                        "Offensive duels per 90","Offensive duels won, %","Progressive runs per 90",
                        "Shots per 90","Touches in box per 90"],
        "Defensive":   ["Aerial duels per 90","Aerial duels won, %","Defensive duels per 90",
                        "Defensive duels won, %","Shots blocked per 90","PAdj Interceptions"],
        "Possession":  ["Deep completions per 90","Dribbles per 90","Successful dribbles, %",
                        "Forward passes per 90","Accurate forward passes, %","Key passes per 90",
                        "Long passes per 90","Accurate long passes, %","Passes per 90","Accurate passes, %",
                        "Passes to final third per 90","Passes to penalty area per 90",
                        "Progressive passes per 90","Accurate progressive passes, %","Smart passes per 90"],
    },
    "GK": {
        "Goalkeeping": ["Exits per 90","Prevented goals per 90","Conceded goals per 90",
                        "Save rate, %","Shots against per 90","xG against per 90"],
        "Possession":  ["Long passes per 90","Accurate long passes, %","Passes per 90","Accurate passes, %"],
        "Defensive":   [],
    },
    "ATT": {
        "Attacking":   ["Crosses per 90","Accurate crosses, %","Non-penalty goals per 90","xG per 90",
                        "Goal conversion, %","xA per 90","Progressive runs per 90",
                        "Shots per 90","Shots on target, %","Touches in box per 90"],
        "Defensive":   ["Aerial duels per 90","Aerial duels won, %","Defensive duels per 90",
                        "Defensive duels won, %","PAdj Interceptions"],
        "Possession":  ["Accelerations per 90","Deep completions per 90","Dribbles per 90",
                        "Successful dribbles, %","Forward passes per 90","Long passes per 90",
                        "Key passes per 90","Passes per 90","Accurate passes, %",
                        "Passes to final third per 90","Passes to penalty area per 90",
                        "Progressive passes per 90","Smart passes per 90"],
    },
}
FEATURE_F_METRICS["ST"] = FEATURE_F_METRICS["CF"]

POS_TO_KEY = {
    "GK": "GK",
    "CB": "CB", "LCB": "CB", "RCB": "CB",
    "LB": "FB", "RB": "FB", "LWB": "FB", "RWB": "FB",
    "DMF": "CM", "LDMF": "CM", "RDMF": "CM", "LCMF": "CM", "RCMF": "CM",
    "AMF": "ATT", "LAMF": "ATT", "RAMF": "ATT",
    "LW": "ATT", "RW": "ATT", "LWF": "ATT", "RWF": "ATT",
    "CF": "CF", "ST": "CF",
}

STAR_LEVELS = [
    "Poor", "Below Average", "Average", "Above Average",
    "Good", "Very Good", "Excellent", "Elite",
]
LEVEL_SUFFIXES = ["GK","CB","FB","CM","ATT","ST","CAM","DM","WB","LB","RB","LW","RW","CF","WG"]

# ── Helpers ───────────────────────────────────────────────────────────────────
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16)/255 for i in (0, 2, 4))

def interp_color(a, b, t):
    return tuple(int(a[i] + (b[i]-a[i])*t) for i in range(3))

def bar_color(pct):
    t = max(0, min(1, pct/100))
    if t <= 0.5:
        rgb = interp_color(TAB_RED, TAB_GOLD, t/0.5)
    else:
        rgb = interp_color(TAB_GOLD, TAB_GREEN, (t-0.5)/0.5)
    return tuple(c/255 for c in rgb)

def stars_html(n, total=5):
    full = "★" * int(n)
    half = "½" if (n % 1 >= 0.5) else ""
    empty = "☆" * (total - int(n) - (1 if half else 0))
    return f'<span style="color:#f6c90e;font-size:18px;">{full}{half}</span><span style="color:#444;font-size:18px;">{empty}</span>'

def load_image_url(url):
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGBA")
    except:
        return None

def get_photo_url(player, team):
    try:
        from photo_utils import get_player_photo_url
        return get_player_photo_url(player, team)
    except:
        return None

def flag_url(country):
    CC = {
        "ghana": "gh", "england": "eng", "scotland": "sct", "wales": "wls",
        "ireland": "ie", "france": "fr", "germany": "de", "spain": "es",
        "italy": "it", "portugal": "pt", "netherlands": "nl", "belgium": "be",
        "brazil": "br", "argentina": "ar", "nigeria": "ng", "senegal": "sn",
        "ivory coast": "ci", "cameroon": "cm", "morocco": "ma", "egypt": "eg",
        "usa": "us", "mexico": "mx", "japan": "jp", "south korea": "kr",
        "australia": "au", "croatia": "hr", "czech republic": "cz", "poland": "pl",
        "denmark": "dk", "sweden": "se", "norway": "no", "switzerland": "ch",
        "austria": "at", "turkey": "tr", "ukraine": "ua", "russia": "ru",
        "serbia": "rs", "romania": "ro", "greece": "gr", "czech": "cz",
    }
    SPECIAL = {
        "eng": "1f3f4-e0067-e0062-e0065-e006e-e0067-e007f",
        "sct": "1f3f4-e0067-e0062-e0073-e0063-e0074-e007f",
        "wls": "1f3f4-e0067-e0062-e0077-e006c-e0073-e007f",
    }
    n = unicodedata.normalize("NFKD", str(country)).encode("ascii","ignore").decode().strip().lower()
    cc = CC.get(n, "")
    if not cc: return ""
    if cc in SPECIAL:
        return f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/svg/{SPECIAL[cc]}.svg"
    base = 0x1F1E6
    code = f"{base+(ord(cc[0].upper())-65):x}-{base+(ord(cc[1].upper())-65):x}"
    return f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/svg/{code}.svg"

# ── Card generator ────────────────────────────────────────────────────────────
def generate_card(cfg, df_league):
    """Generate 1920x1080 scouting card. Returns bytes."""
    DPI = 96
    W, H = 1920/DPI, 1080/DPI

    fig = plt.figure(figsize=(W, H), dpi=DPI)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1920); ax.set_ylim(0, 1080)
    ax.axis("off")
    ax.set_facecolor(BG)
    ax.invert_yaxis()

    club_hex = cfg.get("club_color", "#1a3a6b")
    club_rgb = hex_to_rgb(club_hex)
    bg_rgb   = hex_to_rgb(BG)

    # ── Header gradient (left=club colour, right=BG) ──────────────────────────
    grad_steps = 200
    for i in range(grad_steps):
        t = i / grad_steps
        r = club_rgb[0] + (bg_rgb[0] - club_rgb[0]) * t
        g = club_rgb[1] + (bg_rgb[1] - club_rgb[1]) * t
        b = club_rgb[2] + (bg_rgb[2] - club_rgb[2]) * t
        ax.add_patch(Rectangle((i * 1920/grad_steps, 0), 1920/grad_steps + 1, 330,
                                color=(r, g, b), zorder=0))

    # Dark base below header
    ax.add_patch(Rectangle((0, 330), 1920, 750, color=hex_to_rgb(BG), zorder=0))

    # Subtle section dividers
    ax.plot([900, 900], [330, 1080], color="#1a2540", lw=1, zorder=1)
    ax.plot([1160, 1160], [330, 1080], color="#1a2540", lw=1, zorder=1)

    # ── Player photo ──────────────────────────────────────────────────────────
    photo_img = None
    if cfg.get("photo_url"):
        photo_img = load_image_url(cfg["photo_url"])
    if photo_img is None and cfg.get("player_name") and cfg.get("team"):
        url = get_photo_url(cfg["player_name"], cfg["team"])
        if url: photo_img = load_image_url(url)

    if photo_img:
        from matplotlib.offsetbox import OffsetImage, AnnotationBbox
        photo_arr = np.array(photo_img)
        zoom = 261 / max(photo_img.size)
        ab = AnnotationBbox(OffsetImage(photo_arr, zoom=zoom),
                            (130, 165), frameon=False, zorder=5)
        ax.add_artist(ab)
    else:
        ax.add_patch(Rectangle((0, 0), 261, 330, color="#111827", zorder=2))
        ax.text(130, 165, "📷", fontsize=40, ha="center", va="center",
                color="#4b5563", zorder=3)

    # ── Position diagram (top right) ──────────────────────────────────────────
    if cfg.get("position_image"):
        from matplotlib.offsetbox import OffsetImage, AnnotationBbox
        pos_arr = np.array(cfg["position_image"])
        zoom = min(160/max(cfg["position_image"].size), 1.0)
        ab = AnnotationBbox(OffsetImage(pos_arr, zoom=zoom),
                            (1840, 165), frameon=False, zorder=5)
        ax.add_artist(ab)

    # ── Header text ───────────────────────────────────────────────────────────
    name = cfg.get("player_name", "Player Name")
    pos_label = cfg.get("position_label", "")
    foot = cfg.get("foot", "")
    pos_str = f"{pos_label}   {foot}" if foot else pos_label

    ax.text(280, 55, name, fontsize=44, fontweight="900", color="#ffffff",
            va="top", zorder=5,
            path_effects=[pe.withStroke(linewidth=3, foreground="#000000", alpha=0.4)])
    ax.text(280, 110, pos_str, fontsize=20, fontweight="600", color="#d1d5db", va="top", zorder=5)

    # Age + DOB
    age_txt = f"{cfg.get('age', '')} years old   {cfg.get('dob', '')}" if cfg.get("age") else cfg.get("dob","")
    if age_txt:
        # Flag
        flag = flag_url(cfg.get("nationality",""))
        if flag:
            flag_img = load_image_url(flag)
            if flag_img:
                from matplotlib.offsetbox import OffsetImage, AnnotationBbox
                ab = AnnotationBbox(OffsetImage(np.array(flag_img), zoom=0.35),
                                    (285, 155), frameon=False, zorder=5)
                ax.add_artist(ab)
                ax.text(310, 148, age_txt, fontsize=16, color="#d1d5db", va="top", zorder=5)
            else:
                ax.text(280, 148, age_txt, fontsize=16, color="#d1d5db", va="top", zorder=5)
        else:
            ax.text(280, 148, age_txt, fontsize=16, color="#d1d5db", va="top", zorder=5)

    # ── Team badge + info ─────────────────────────────────────────────────────
    badge_x = 620
    if cfg.get("badge_url"):
        badge_img = load_image_url(cfg["badge_url"])
        if badge_img:
            from matplotlib.offsetbox import OffsetImage, AnnotationBbox
            zoom = 80 / max(badge_img.size)
            ab = AnnotationBbox(OffsetImage(np.array(badge_img), zoom=zoom),
                                (badge_x + 40, 80), frameon=False, zorder=5)
            ax.add_artist(ab)

    ax.text(badge_x + 95, 45, cfg.get("team",""), fontsize=20, fontweight="800",
            color="#ffffff", va="top", zorder=5)
    ax.text(badge_x + 95, 78, cfg.get("league",""), fontsize=15, color="#9ca3af", va="top", zorder=5)
    ax.text(badge_x + 95, 105, cfg.get("importance",""), fontsize=13, color="#6b7280", va="top", zorder=5)

    # ── Stats: Height / Value / Contract ─────────────────────────────────────
    stats_x = 870
    for row_i, (label, val) in enumerate([
        ("Height:", cfg.get("height","")),
        ("Value:",  cfg.get("value","")),
        ("Contract:", cfg.get("contract","")),
    ]):
        y = 45 + row_i * 40
        ax.text(stats_x, y, label, fontsize=13, color="#9ca3af", va="top", zorder=5)
        ax.text(stats_x + 80, y, str(val), fontsize=13, fontweight="700",
                color="#ffffff", va="top", zorder=5)

    # ── Nav bar line ──────────────────────────────────────────────────────────
    ax.plot([0, 1160], [200, 200], color="#1a2540", lw=1, zorder=3)
    for i, tab in enumerate(["Profile ▸", "Performance ▾", "Similar Players ▾", "Club Fit ▾", "Video ▾", "Compare ▾"]):
        ax.text(280 + i*115, 215, tab, fontsize=11, color="#6b7280", va="top", zorder=5)

    # ── Season Stats row ─────────────────────────────────────────────────────
    ax.add_patch(Rectangle((0, 330), 900, 28, color="#0d1117", zorder=2))
    ax.text(10, 333, "Season Stats", fontsize=12, fontweight="800",
            color=ACCENT_PINK, va="top", zorder=5)
    ss_cols = ["Apps","Gls","Asts","xG","xA","Mins","Av.Rat"]
    ss_vals = [cfg.get("apps",""), cfg.get("goals",""), cfg.get("assists",""),
               cfg.get("xg",""), cfg.get("xa",""), cfg.get("mins",""), cfg.get("avg_rating","")]
    for j, (col, val) in enumerate(zip(ss_cols, ss_vals)):
        x = 140 + j*100
        ax.text(x, 333, col, fontsize=9, color="#6b7280", va="top", ha="center", zorder=5)
        # Rating gets a coloured badge
        if col == "Av.Rat" and val:
            try:
                rv = float(val)
                badge_col = "#ef4444" if rv < 6.5 else "#f59e0b" if rv < 7.0 else "#22c55e"
                ax.add_patch(FancyBboxPatch((x-18, 342), 36, 16,
                             boxstyle="round,pad=2", facecolor=badge_col, zorder=4))
                ax.text(x, 350, str(val), fontsize=10, fontweight="800",
                        color="#fff", ha="center", va="center", zorder=5)
            except:
                ax.text(x, 344, str(val), fontsize=10, fontweight="700",
                        color="#fff", ha="center", va="top", zorder=5)
        else:
            ax.text(x, 344, str(val), fontsize=10, fontweight="700",
                    color="#fff", ha="center", va="top", zorder=5)

    # ── Feature F bar chart ───────────────────────────────────────────────────
    pos_tok = str(cfg.get("position_token","CF")).strip().upper()
    feat_key = POS_TO_KEY.get(pos_tok, "CF")
    sections = FEATURE_F_METRICS.get(feat_key, FEATURE_F_METRICS["CF"])

    chart_top = 365
    chart_left = 0
    chart_right = 895
    chart_w = chart_right - chart_left

    y_cursor = chart_top
    player_row = None
    if df_league is not None and cfg.get("player_name"):
        matches = df_league[df_league["Player"].astype(str).str.lower() == cfg["player_name"].strip().lower()]
        if not matches.empty:
            player_row = matches.iloc[0]

    row_h = 11.5
    label_w = 160
    bar_l = chart_left + label_w
    bar_max_w = chart_w - label_w - 55
    val_x = chart_right - 5

    for sec_name, metrics in sections.items():
        metrics = [m for m in metrics if m]  # filter empty
        if not metrics: continue

        # Section header
        ax.text(chart_left + 10, y_cursor + 2, sec_name,
                fontsize=12, fontweight="800", color="#ffffff",
                va="top", zorder=5)
        y_cursor += 18

        for metric in metrics:
            # Compute percentile vs league pool
            pct = 50.0
            raw_val = ""
            if player_row is not None and df_league is not None:
                col = metric
                if col in df_league.columns and col in player_row.index:
                    pool = pd.to_numeric(df_league[col], errors="coerce").dropna()
                    v = pd.to_numeric(player_row.get(col, np.nan), errors="coerce")
                    if pd.notna(v) and not pool.empty:
                        pct = float((pool <= v).mean() * 100)
                        # Format raw value
                        if "%" in metric:
                            raw_val = f"{int(round(v))}%"
                        elif v == int(v):
                            raw_val = str(int(v))
                        else:
                            raw_val = f"{v:.2f}"

            bar_w = bar_max_w * (pct / 100)
            bc = bar_color(pct)

            # Track
            ax.add_patch(Rectangle((bar_l, y_cursor + 1), bar_max_w, row_h - 3,
                                    color=hex_to_rgb(BAR_TRACK), zorder=2))
            # Fill
            if bar_w > 0:
                ax.add_patch(Rectangle((bar_l, y_cursor + 1), bar_w, row_h - 3,
                                        color=bc, zorder=3))

            # 50th percentile dashed line
            ax.plot([bar_l + bar_max_w*0.5]*2, [y_cursor+1, y_cursor+row_h-2],
                    color="#ffffff", lw=1, ls=(0,(3,3)), alpha=0.6, zorder=4)

            # Label
            short = metric.replace(" per 90","").replace(", %"," %").replace("Accurate ","")
            ax.text(chart_left + 8, y_cursor + row_h/2, short,
                    fontsize=7.5, color=LABEL_COL, va="center", zorder=5)

            # Raw value inside bar
            if raw_val:
                ax.text(bar_l + 4, y_cursor + row_h/2, raw_val,
                        fontsize=7, color="#0a0a0a", fontweight="700", va="center", zorder=6)

            y_cursor += row_h

        y_cursor += 6  # gap between sections

    # x-axis labels
    for pct_tick in [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        x = bar_l + bar_max_w * pct_tick/100
        ax.text(x, y_cursor + 2, f"{pct_tick}%", fontsize=7, color="#4b5563",
                ha="center", va="top", zorder=5)
    ax.text(bar_l + bar_max_w/2, y_cursor + 12, "Percentile Rank",
            fontsize=8, color="#4b5563", ha="center", va="top", zorder=5)

    # ── Right panel: Key Attributes / Dev Areas / View ────────────────────────
    rx = 910
    rw = 245
    ry = 355

    def write_bullet(label, text, y_start):
        ax.text(rx, y_start, f"• ", fontsize=12, color=ACCENT_PINK, va="top", zorder=5)
        ax.text(rx + 12, y_start, f"{label}: ", fontsize=12, fontweight="700",
                color=ACCENT_PINK, va="top", zorder=5)
        # Wrap text
        words = text.split()
        lines, line = [], []
        for w in words:
            line.append(w)
            if len(" ".join(line)) > 32:
                lines.append(" ".join(line[:-1]))
                line = [w]
        if line: lines.append(" ".join(line))
        label_w_px = 70
        ax.text(rx + label_w_px, y_start, lines[0] if lines else "", fontsize=11,
                color="#e8eef8", va="top", zorder=5, wrap=True)
        for li, l in enumerate(lines[1:], 1):
            ax.text(rx, y_start + li*16, l, fontsize=11, color="#e8eef8", va="top", zorder=5)
        return y_start + max(len(lines), 1)*16 + 12

    ry = write_bullet("Key Attributes", cfg.get("key_attributes",""), ry)
    ry += 8
    ry = write_bullet("Development Areas", cfg.get("dev_areas",""), ry)
    ry += 8
    ry = write_bullet("View", cfg.get("view",""), ry)
    ry += 20

    # Current/Potential Level
    def draw_level(label, stars, level_text, y):
        ax.text(rx, y, label, fontsize=12, fontweight="800", color="#ffffff", va="top", zorder=5)
        y += 20
        # Stars
        for si in range(5):
            filled = si < int(stars)
            half = (not filled) and (si == int(stars)) and (stars % 1 >= 0.5)
            color = "#f6c90e" if (filled or half) else "#2a3450"
            ax.text(rx + si*22, y, "★", fontsize=18, color=color, va="top", zorder=5)
        ax.text(rx + 120, y + 2, level_text, fontsize=11, color="#9ca3af", va="top", zorder=5)
        return y + 30

    ry = draw_level("CURRENT LEVEL", cfg.get("current_stars",3), cfg.get("current_level",""), ry)
    ry += 5
    ry = draw_level("POTENTIAL LEVEL", cfg.get("potential_stars",4), cfg.get("potential_level",""), ry)

    # ── Far right: Best Role / Performance Trend / Physical / Form ────────────
    frx = 1170
    fry = 340

    # BEST ROLE header
    ax.text(frx, fry, "BEST ROLE", fontsize=11, fontweight="900",
            color="#ffffff", va="top", zorder=5, letter_spacing=2)
    fry += 22

    roles = cfg.get("roles", [])
    for ri, (role_name, role_score) in enumerate(roles[:3]):
        score = int(role_score)
        sc = bar_color(score)
        # Pill background
        ax.add_patch(FancyBboxPatch((frx, fry), 170, 22,
                     boxstyle="round,pad=3", facecolor="#111827", zorder=3))
        ax.text(frx + 8, fry + 11, role_name, fontsize=10, color="#d1d5db",
                va="center", zorder=5)
        # Score badge
        ax.add_patch(FancyBboxPatch((frx + 148, fry + 2), 26, 18,
                     boxstyle="round,pad=2", facecolor=sc, zorder=4))
        ax.text(frx + 161, fry + 11, str(score), fontsize=10, fontweight="800",
                color="#000" if score > 50 else "#fff", ha="center", va="center", zorder=5)
        fry += 28

    # PERFORMANCE TREND
    fry += 10
    ax.text(frx, fry, "PERFORMANCE TREND", fontsize=10, fontweight="900",
            color="#ffffff", va="top", zorder=5)
    fry += 20

    trend_data = cfg.get("trend_data", [])  # list of (season_label, score)
    if len(trend_data) >= 2:
        tw = 200
        th = 60
        # Normalize scores to plot area
        scores = [d[1] for d in trend_data]
        s_min, s_max = min(scores)-5, max(scores)+5
        def ty(s): return fry + th - (s - s_min) / max(s_max - s_min, 1) * th

        xs = [frx + i*(tw/(len(trend_data)-1)) for i in range(len(trend_data))]
        ys = [ty(s) for s in scores]

        ax.plot(xs, ys, color=TREND_CYAN, lw=2.5, zorder=5)
        for xi, yi, (season, score) in zip(xs, ys, trend_data):
            ax.scatter([xi], [yi], s=60, color=TREND_CYAN, zorder=6)
            ax.text(xi, yi - 12, str(score), fontsize=9, fontweight="800",
                    color="#ffffff", ha="center", va="top", zorder=7)
            ax.text(xi, fry + th + 6, season, fontsize=8, color="#6b7280",
                    ha="center", va="top", zorder=5)
        fry += th + 28
    else:
        fry += 20

    # PHYSICAL dots
    ax.text(frx, fry, "PHYSICAL", fontsize=10, fontweight="900",
            color="#ffffff", va="top", zorder=5)
    fry += 18

    physical = cfg.get("physical", {"Pace": 4, "Power": 3, "Fitness": 3})
    dot_colors = {5:"#22c55e", 4:"#4ade80", 3:"#facc15", 2:"#f97316", 1:"#ef4444"}
    for attr, dots in physical.items():
        ax.text(frx, fry + 6, attr, fontsize=10, color="#9ca3af", va="center", zorder=5)
        for di in range(5):
            filled = di < dots
            col = dot_colors.get(dots, "#22c55e") if filled else "#1a2540"
            ax.scatter([frx + 70 + di*22], [fry + 6], s=55,
                       color=col, zorder=5, edgecolors="#0a0f1c", linewidths=1)
        fry += 22

    # FORM
    fry += 8
    ax.text(frx, fry, "FORM", fontsize=10, fontweight="900",
            color="#ffffff", va="top", zorder=5)
    fry += 18

    form_colors_map = {
        "W": "#22c55e", "D": "#f59e0b", "L": "#ef4444",
        "G": "#22c55e",  # Good
        "A": "#f59e0b",  # Average
        "P": "#ef4444",  # Poor
    }
    form = cfg.get("form", [])
    for fi, result in enumerate(form[:5]):
        col = form_colors_map.get(result.upper(), "#4b5563")
        ax.add_patch(FancyBboxPatch((frx + fi*28, fry), 22, 22,
                     boxstyle="round,pad=2", facecolor=col, zorder=4))

    if cfg.get("avg_rating_5"):
        fry += 30
        ax.add_patch(FancyBboxPatch((frx, fry), 90, 18,
                     boxstyle="round,pad=2", facecolor="#0d1424", zorder=3))
        ax.text(frx + 6, fry + 9, f"⭐ {cfg['avg_rating_5']}  Last 5 Avg Rating",
                fontsize=8, color="#9ca3af", va="center", zorder=5)

    fig.tight_layout(pad=0)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()




# ── Role score weights (same as position pages) ───────────────────────────────
ROLE_BUCKETS_SIMPLE = {
    "CF": {
        "Goal Threat CF":  {"Non-penalty goals per 90":3,"Shots per 90":1.5,"xG per 90":3,"Touches in box per 90":1,"Shots on target, %":0.5},
        "Link Up CF":      {"Passes per 90":2,"xA per 90":3,"Dribbles per 90":2,"Progressive runs per 90":2,"Deep completions per 90":1},
        "Target Man CF":   {"Aerial duels per 90":3,"Aerial duels won, %":5},
    },
    "CB": {
        "Ball Playing CB": {"Passes per 90":2,"Accurate passes, %":2,"Progressive passes per 90":2,"Progressive runs per 90":1.5,"Accurate long passes, %":1},
        "Box Defender":    {"Aerial duels won, %":3,"PAdj Interceptions":2,"Shots blocked per 90":1,"Defensive duels won, %":4},
        "Wide CB":         {"Defensive duels won, %":2,"Dribbles per 90":2,"Progressive runs per 90":2,"Forward passes per 90":1},
    },
    "FB": {
        "Build Up FB":     {"Passes per 90":2,"Progressive passes per 90":2.5,"Progressive runs per 90":2,"xA per 90":1},
        "Attacking FB":    {"Crosses per 90":2,"Dribbles per 90":3.5,"Touches in box per 90":2,"Progressive runs per 90":3,"xA per 90":3},
        "Defensive FB":    {"Defensive duels per 90":2,"PAdj Interceptions":3,"Defensive duels won, %":3.5},
    },
    "CM": {
        "Deep Playmaker CM":   {"Passes per 90":1,"Progressive passes per 90":3,"Passes to final third per 90":2.5,"Accurate long passes, %":1},
        "Advanced Playmaker CM": {"xA per 90":4,"Passes to penalty area per 90":2,"Smart passes per 90":2},
        "Defensive CM":        {"Defensive duels per 90":4,"Defensive duels won, %":4,"PAdj Interceptions":3},
        "Ball Carrying CM":    {"Dribbles per 90":4,"Progressive runs per 90":3,"Accelerations per 90":3},
    },
    "ATT": {
        "Goal Threat ATT": {"xG per 90":3,"Non-penalty goals per 90":3,"Shots per 90":2,"Touches in box per 90":2},
        "Playmaker ATT":   {"xA per 90":3,"Key passes per 90":1,"Smart passes per 90":1.5,"Passes to penalty area per 90":2},
        "Ball Carrier ATT":{"Dribbles per 90":4,"Progressive runs per 90":3,"Accelerations per 90":3},
    },
    "GK": {
        "Shot Stopper GK": {"Save rate, %":1,"Prevented goals per 90":3},
        "Ball Playing GK": {"Accurate passes, %":3,"Accurate long passes, %":2},
        "Sweeper GK":      {"Exits per 90":1},
    },
}
ROLE_BUCKETS_SIMPLE["ST"] = ROLE_BUCKETS_SIMPLE["CF"]

def _pos_key(pos_str):
    tok = str(pos_str).split(",")[0].strip().upper()
    return {
        "GK":"GK","CB":"CB","LCB":"CB","RCB":"CB",
        "LB":"FB","RB":"FB","LWB":"FB","RWB":"FB",
        "DMF":"CM","LDMF":"CM","RDMF":"CM","LCMF":"CM","RCMF":"CM",
        "AMF":"ATT","LAMF":"ATT","RAMF":"ATT","LW":"ATT","RW":"ATT","LWF":"ATT","RWF":"ATT",
        "CF":"CF","ST":"CF",
    }.get(tok, "CF")

def compute_best_role_score(row, df_pool, pos_key):
    """Compute best role score for a player row vs a pool DataFrame."""
    roles = ROLE_BUCKETS_SIMPLE.get(pos_key, ROLE_BUCKETS_SIMPLE["CF"])
    best_score = 0.0
    best_name  = ""
    for role_name, metrics in roles.items():
        wsum, wtot = 0.0, 0.0
        for met, w in metrics.items():
            if met not in df_pool.columns or met not in row.index:
                continue
            pool = pd.to_numeric(df_pool[met], errors="coerce").dropna()
            v    = pd.to_numeric(row.get(met, np.nan), errors="coerce")
            if pd.isna(v) or pool.empty:
                continue
            pct   = float((pool <= v).mean() * 100)
            wsum += pct * w
            wtot += w
        if wtot > 0:
            score = wsum / wtot
            if score > best_score:
                best_score = score
                best_name  = role_name
    return best_name, round(best_score)


@st.cache_data(show_spinner=False)
def load_all_season_csvs():
    """Load all *WORLDFULL.csv files from cwd, return dict {season: df}."""
    season_dfs = {}
    for p in sorted(Path.cwd().glob("*.csv")):
        try:
            df = pd.read_csv(str(p), low_memory=False)
            if "Wyscout ID" in df.columns and "Season" in df.columns:
                # Normalise season
                def norm(s):
                    s = str(s).strip()
                    if "-" in s: return s
                    try:
                        y = int(float(s)); return f"{y-1}-{str(y)[2:]}"
                    except: return s
                df["Season"] = df["Season"].apply(norm)
                seasons = df["Season"].dropna().unique()
                for season in seasons:
                    chunk = df[df["Season"] == season].copy()
                    if season not in season_dfs:
                        season_dfs[season] = chunk
                    else:
                        season_dfs[season] = pd.concat([season_dfs[season], chunk], ignore_index=True)
        except Exception:
            pass
    return season_dfs


def get_career_history(wyscout_id, season_dfs, pos_key):
    """
    Look up a player by Wyscout ID across all season CSVs.
    Returns list of dicts per season, sorted oldest→newest.
    Each dict: {season, team, league, apps, mins, goals, assists, xg, xa, best_role, best_role_score}
    """
    if not wyscout_id or not season_dfs:
        return []

    rows = []
    for season, df in season_dfs.items():
        df["Wyscout ID"] = pd.to_numeric(df["Wyscout ID"], errors="coerce")
        match = df[df["Wyscout ID"] == int(wyscout_id)]
        if match.empty:
            continue
        row = match.iloc[0]

        # Pool for percentiles = same league same season
        league = str(row.get("League",""))
        pool = df[df["League"] == league] if league else df

        # Position key from this season's data
        pk = _pos_key(str(row.get("Position",""))) if str(row.get("Position","")).strip() else pos_key

        role_name, role_score = compute_best_role_score(row, pool, pk)

        def safe(col, fmt=None):
            v = row.get(col, "")
            try:
                v = float(v)
                if fmt: return fmt.format(v)
                return str(int(v)) if v == int(v) else f"{v:.1f}"
            except:
                return str(v) if v else ""

        rows.append({
            "season":          season,
            "team":            str(row.get("Team","")),
            "league":          league,
            "apps":            safe("Matches played"),
            "mins":            safe("Minutes played"),
            "goals":           safe("Goals"),
            "assists":         safe("Assists"),
            "xg":              safe("xG", "{:.1f}"),
            "xa":              safe("xA", "{:.1f}"),
            "best_role":       role_name,
            "best_role_score": role_score,
        })

    rows.sort(key=lambda r: r["season"])
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
# STREAMLIT UI
# ═══════════════════════════════════════════════════════════════════════════════
st.title("🃏 Scouting Card Generator")
st.caption("Generates a 1920×1080 player scouting card matching your Canva template")

with st.sidebar:
    st.markdown("## 📁 Data")

    # CSV selector — primary season for stats + percentiles
    csv_candidates = sorted(Path.cwd().glob("*.csv"), key=lambda f: f.stat().st_mtime, reverse=True)
    csv_names = [f.name for f in csv_candidates]

    if csv_names:
        selected_csv = st.selectbox("Primary season CSV", csv_names, index=0,
                                     help="Used for Feature F percentile bars")
        uploaded_csv = st.file_uploader("Or upload CSV", type="csv")
    else:
        selected_csv = None
        uploaded_csv = st.file_uploader("Upload CSV", type="csv")

    st.caption("Career history auto-loads from all *WORLDFULL CSVs in this folder")

@st.cache_data(show_spinner=False)
def load_csv(path):
    return pd.read_csv(path, low_memory=False)

@st.cache_data(show_spinner=False)
def load_csv_bytes(data):
    import io
    return pd.read_csv(io.BytesIO(data), low_memory=False)

df = None
if uploaded_csv:
    df = load_csv_bytes(uploaded_csv.getvalue())
elif selected_csv:
    df = load_csv(str(Path.cwd() / selected_csv))

# ── Two column layout ─────────────────────────────────────────────────────────
col_form, col_preview = st.columns([1, 1])

with col_form:
    st.markdown("### Player")
    c1, c2 = st.columns(2)
    player_name = c1.text_input("Player name", "Prince Adu")
    team        = c2.text_input("Team", "Viktoria Plzen")

    c3, c4 = st.columns(2)
    league      = c3.text_input("League", "Chance Liga")
    position_label = c4.text_input("Position label", "Center Forward (ST)")

    c5, c6, c7 = st.columns(3)
    age         = c5.text_input("Age", "22")
    dob         = c6.text_input("Date of birth", "23/9/2003")
    foot        = c7.selectbox("Foot", ["Right","Left","Both"])

    c8, c9 = st.columns(2)
    nationality = c8.text_input("Nationality", "Ghana")
    importance  = c9.text_input("Importance", "Important Player")

    c10, c11, c12 = st.columns(3)
    height    = c10.text_input("Height", "5'11")
    value     = c11.text_input("Value", "€3m")
    contract  = c12.text_input("Contract", "2027")

    st.markdown("### Club")
    c13, c14 = st.columns(2)
    club_color = c13.text_input("Club colour (hex)", "#1a3a6b",
                                 help="Header gradient fades from this colour")
    badge_url  = c14.text_input("Badge URL (optional)", "")

    st.markdown("### Season Stats")
    cs1,cs2,cs3,cs4,cs5,cs6,cs7 = st.columns(7)
    apps       = cs1.text_input("Apps","13(8)")
    goals      = cs2.text_input("Gls","6")
    assists    = cs3.text_input("Asts","1")
    xg         = cs4.text_input("xG","5.8")
    xa         = cs5.text_input("xA","1.7")
    mins       = cs6.text_input("Mins","1,320")
    avg_rating = cs7.text_input("Av.Rat","6.9")

    st.markdown("### Photo")
    photo_url   = st.text_input("Photo URL (optional — auto-fetched if blank)", "")
    pos_img_up  = st.file_uploader("Position diagram image", type=["png","jpg","webp"])

    st.markdown("### Position token (for bar chart)")
    pos_tok = st.selectbox("Position token", ["CF","ST","CB","LCB","RCB","LB","RB","LWB","RWB",
                                               "DMF","LDMF","RDMF","LCMF","RCMF",
                                               "AMF","LAMF","RAMF","LW","RW","LWF","RWF","GK"])

    st.markdown("### Scouting Notes")
    key_attributes = st.text_area("Key Attributes",
        "Acceleration, pace, taking contact, penalty-box instinct & movement, unpredictability, ball control, dribbling, channel running", height=80)
    dev_areas = st.text_area("Development Areas", "Finishing, availability, consistency", height=60)
    view      = st.text_area("View",
        "Fitness / injuries have stalled initial excellent progress and struggles for consistent run of form but natural talent and ability. Differential skillset, not quite target man but suits.", height=100)

    st.markdown("### Roles")
    roles = []
    for ri in range(3):
        rc1, rc2 = st.columns([3,1])
        rname = rc1.text_input(f"Role {ri+1} name", ["Target Man ST","Goal Threat ST","Link-Up ST"][ri], key=f"rn{ri}")
        rscore= rc2.text_input(f"Score", ["49","79","78"][ri], key=f"rs{ri}")
        if rname:
            try: roles.append((rname, int(rscore)))
            except: roles.append((rname, 0))

    st.markdown("### Level")
    lc1, lc2 = st.columns(2)
    current_stars  = lc1.slider("Current stars", 0.0, 5.0, 3.5, 0.5)
    potential_stars= lc2.slider("Potential stars", 0.0, 5.0, 4.0, 0.5)
    current_level  = lc1.text_input("Current level label", "Very Good Champ ST")
    potential_level= lc2.text_input("Potential level label", "Good Top 5 EU League ST")

    st.markdown("### Performance Trend")
    trend_mode = st.radio("Trend source", ["Auto (from CSVs via Wyscout ID)", "Manual"],
                           horizontal=True, key="trend_mode")
    wyscout_id_input = st.text_input("Wyscout ID (for auto trend + career history)", "",
                                      help="Found in your CSV — used to look up player across all seasons")
    trend_data = []
    career_rows = []

    if trend_mode == "Manual":
        st.caption("Enter season + best role score pairs (oldest→newest)")
        for ti in range(5):
            tc1, tc2 = st.columns(2)
            season = tc1.text_input(f"Season {ti+1}", "", key=f"ts{ti}")
            score  = tc2.text_input(f"Score", "", key=f"tv{ti}")
            if season and score:
                try: trend_data.append((season, int(score)))
                except: pass

    st.markdown("### Physical (1–5 dots)")
    ph1, ph2, ph3 = st.columns(3)
    pace    = ph1.slider("Pace",    1, 5, 5)
    power   = ph2.slider("Power",   1, 5, 4)
    fitness = ph3.slider("Fitness", 1, 5, 3)

    st.markdown("### Form (last 5)")
    st.caption("W=Win(green) D=Draw(amber) L=Loss(red)")
    form_str = st.text_input("Form (5 letters e.g. WDWLW)", "DWLLW")
    avg_5    = st.text_input("Last 5 avg rating", "6.3")

    generate_btn = st.button("🖼 Generate Card", type="primary", use_container_width=True)

with col_preview:
    st.markdown("### Preview")

    if generate_btn:
        pos_image = None
        if pos_img_up:
            pos_image = Image.open(pos_img_up).convert("RGBA")

        # Build league pool for percentiles
        df_league = None
        if df is not None:
            mask = df["League"].astype(str).str.lower() == league.strip().lower()
            df_league = df[mask].copy() if mask.any() else df.copy()

        # Career history + auto trend via Wyscout ID
        pos_key_for_career = POS_TO_KEY.get(pos_tok, "CF")
        if trend_mode == "Auto (from CSVs via Wyscout ID)" and wyscout_id_input.strip():
            with st.spinner("Loading career history from all season CSVs…"):
                season_dfs = load_all_season_csvs()
                career_rows = get_career_history(
                    wyscout_id_input.strip(), season_dfs, pos_key_for_career
                )
            trend_data = [(r["season"], r["best_role_score"]) for r in career_rows if r["best_role_score"] > 0]
        else:
            career_rows = []

        cfg = dict(
            player_name=player_name, team=team, league=league,
            position_label=position_label, position_token=pos_tok,
            age=age, dob=dob, foot=foot, nationality=nationality,
            importance=importance, height=height, value=value, contract=contract,
            club_color=club_color, badge_url=badge_url, photo_url=photo_url,
            position_image=pos_image,
            apps=apps, goals=goals, assists=assists,
            xg=xg, xa=xa, mins=mins, avg_rating=avg_rating,
            key_attributes=key_attributes, dev_areas=dev_areas, view=view,
            roles=roles,
            current_stars=current_stars, current_level=current_level,
            potential_stars=potential_stars, potential_level=potential_level,
            trend_data=trend_data,
            career_rows=career_rows,
            physical={"Pace": pace, "Power": power, "Fitness": fitness},
            form=list(form_str.upper()[:5]),
            avg_rating_5=avg_5,
        )

        with st.spinner("Generating card…"):
            png_bytes = generate_card(cfg, df_league)

        st.image(png_bytes, use_column_width=True)
        st.download_button(
            "⬇️ Download PNG",
            data=png_bytes,
            file_name=f"{player_name.replace(' ','_')}_scouting_card.png",
            mime="image/png",
        )

        # Career history table
        if career_rows:
            st.markdown("#### Career History (auto from CSVs)")
            career_df = pd.DataFrame(career_rows)[
                ["season","team","league","apps","mins","goals","assists","xg","xa","best_role","best_role_score"]
            ]
            career_df.columns = ["Season","Team","League","Apps","Mins","G","A","xG","xA","Best Role","Score"]
            st.dataframe(career_df, use_container_width=True, hide_index=True)
    else:
        st.info("Fill in the form and click **Generate Card** to preview.")
        st.markdown("""
**What auto-fills from CSV:**
- All bar chart percentile ranks (Feature F)
- Computed vs players in same league

**What you fill in manually:**
- Key Attributes, Development Areas, View
- Physical dots, Form, Role scores
- Current/Potential level + stars
- Club colour hex for header gradient
- Position diagram image upload
        """)

# ═══════════════════════════════════════════════════════════════════════════════
# CAREER HISTORY + AUTO TREND (appended)
# ═══════════════════════════════════════════════════════════════════════════════