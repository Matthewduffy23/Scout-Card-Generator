# app.py — Scouting Card Generator (HTML/CSS renderer)
# Canvas: 1920x1080px | Font: Montserrat | Background: #0a0f1c

import io, unicodedata, base64
from pathlib import Path

import streamlit as st
import pandas as pd
import numpy as np
import requests

# Install playwright chromium on first run
import subprocess, sys
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        p.chromium.launch(args=["--no-sandbox"]).close()
except Exception:
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)

st.set_page_config(page_title="Scouting Card Generator", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&display=swap');
html,body,[class*="css"]{font-family:'Montserrat',sans-serif!important;}
.stApp{background:#0a0f1c!important;color:#fff!important;}
section[data-testid="stSidebar"]{background:#060a14!important;border-right:1px solid #1a2540!important;}
section[data-testid="stSidebar"] *{color:#fff!important;}
div[data-baseweb="select"] *{background:#0d1424!important;color:#fff!important;}
div[data-baseweb="popover"] *{background:#0d1424!important;color:#fff!important;}
.stTextInput>div>div>input,.stTextArea textarea{background:#0d1424!important;border:1px solid #1e2d4a!important;color:#fff!important;}
.stButton>button{background:#fff!important;color:#000!important;font-weight:700!important;border:none!important;border-radius:4px!important;}
label{color:#9ca3af!important;font-size:11px!important;letter-spacing:.1em!important;text-transform:uppercase!important;}
h1,h2,h3{color:#fff!important;}
</style>
""", unsafe_allow_html=True)

TAB_RED   = (199, 54,  60)
TAB_GOLD  = (240, 197, 106)
TAB_GREEN = (61,  166, 91)

FEATURE_F = {
    "CF":{
        "Attacking":["Crosses per 90","Accurate crosses, %","Non-penalty goals per 90","xG per 90","Goal conversion, %","Head goals per 90","xA per 90","Progressive runs per 90","Shots per 90","Shots on target, %","Touches in box per 90"],
        "Defensive":["Aerial duels per 90","Aerial duels won, %","Defensive duels per 90","Defensive duels won, %","PAdj Interceptions"],
        "Possession":["Deep completions per 90","Dribbles per 90","Successful dribbles, %","Key passes per 90","Passes per 90","Accurate passes, %","Passes to penalty area per 90","Smart passes per 90"],
    },
    "CB":{
        "Attacking":["Non-penalty goals per 90","xG per 90","Offensive duels per 90","Offensive duels won, %","Progressive runs per 90"],
        "Defensive":["Aerial duels per 90","Aerial duels won, %","Defensive duels per 90","Defensive duels won, %","PAdj Interceptions","Shots blocked per 90"],
        "Possession":["Passes per 90","Accurate passes, %","Forward passes per 90","Accurate forward passes, %","Progressive passes per 90","Accurate progressive passes, %","Long passes per 90","Accurate long passes, %"],
    },
    "FB":{
        "Attacking":["Crosses per 90","Accurate crosses, %","Non-penalty goals per 90","xG per 90","xA per 90","Offensive duels per 90","Offensive duels won, %","Progressive runs per 90","Shots per 90","Shots on target, %","Touches in box per 90"],
        "Defensive":["Aerial duels per 90","Aerial duels won, %","Defensive duels per 90","Defensive duels won, %","Shots blocked per 90","PAdj Interceptions"],
        "Possession":["Deep completions per 90","Dribbles per 90","Successful dribbles, %","Forward passes per 90","Long passes per 90","Key passes per 90","Passes per 90","Accurate passes, %","Passes to final third per 90","Passes to penalty area per 90","Progressive passes per 90","Smart passes per 90"],
    },
    "CM":{
        "Attacking":["Crosses per 90","Non-penalty goals per 90","xG per 90","xA per 90","Offensive duels per 90","Offensive duels won, %","Progressive runs per 90","Shots per 90","Touches in box per 90"],
        "Defensive":["Aerial duels per 90","Aerial duels won, %","Defensive duels per 90","Defensive duels won, %","Shots blocked per 90","PAdj Interceptions"],
        "Possession":["Deep completions per 90","Dribbles per 90","Successful dribbles, %","Forward passes per 90","Accurate forward passes, %","Key passes per 90","Long passes per 90","Accurate long passes, %","Passes per 90","Accurate passes, %","Passes to final third per 90","Passes to penalty area per 90","Progressive passes per 90","Accurate progressive passes, %","Smart passes per 90"],
    },
    "GK":{
        "Goalkeeping":["Exits per 90","Prevented goals per 90","Conceded goals per 90","Save rate, %","Shots against per 90","xG against per 90"],
        "Possession":["Long passes per 90","Accurate long passes, %","Passes per 90","Accurate passes, %"],
        "Defensive":[],
    },
    "ATT":{
        "Attacking":["Crosses per 90","Accurate crosses, %","Non-penalty goals per 90","xG per 90","Goal conversion, %","xA per 90","Progressive runs per 90","Shots per 90","Shots on target, %","Touches in box per 90"],
        "Defensive":["Aerial duels per 90","Aerial duels won, %","Defensive duels per 90","Defensive duels won, %","PAdj Interceptions"],
        "Possession":["Accelerations per 90","Deep completions per 90","Dribbles per 90","Successful dribbles, %","Forward passes per 90","Long passes per 90","Key passes per 90","Passes per 90","Accurate passes, %","Passes to final third per 90","Passes to penalty area per 90","Progressive passes per 90","Smart passes per 90"],
    },
}
FEATURE_F["ST"]=FEATURE_F["CF"]

POS_KEY={"GK":"GK","CB":"CB","LCB":"CB","RCB":"CB","LB":"FB","RB":"FB","LWB":"FB","RWB":"FB","DMF":"CM","LDMF":"CM","RDMF":"CM","LCMF":"CM","RCMF":"CM","AMF":"ATT","LAMF":"ATT","RAMF":"ATT","LW":"ATT","RW":"ATT","LWF":"ATT","RWF":"ATT","CF":"CF","ST":"CF"}

ROLES={
    "CF":{"Goal Threat CF":{"Non-penalty goals per 90":3,"Shots per 90":1.5,"xG per 90":3,"Touches in box per 90":1},"Link Up CF":{"Passes per 90":2,"xA per 90":3,"Dribbles per 90":2,"Progressive runs per 90":2},"Target Man CF":{"Aerial duels per 90":3,"Aerial duels won, %":5}},
    "CB":{"Ball Playing CB":{"Passes per 90":2,"Accurate passes, %":2,"Progressive passes per 90":2,"Progressive runs per 90":1.5},"Box Defender":{"Aerial duels won, %":3,"PAdj Interceptions":2,"Defensive duels won, %":4},"Wide CB":{"Defensive duels won, %":2,"Dribbles per 90":2,"Progressive runs per 90":2}},
    "FB":{"Build Up FB":{"Passes per 90":2,"Progressive passes per 90":2.5,"Progressive runs per 90":2,"xA per 90":1},"Attacking FB":{"Crosses per 90":2,"Dribbles per 90":3.5,"Progressive runs per 90":3,"xA per 90":3},"Defensive FB":{"Defensive duels per 90":2,"PAdj Interceptions":3,"Defensive duels won, %":3.5}},
    "CM":{"Deep Playmaker":{"Passes per 90":1,"Progressive passes per 90":3,"Passes to final third per 90":2.5},"Advanced Playmaker":{"xA per 90":4,"Passes to penalty area per 90":2,"Smart passes per 90":2},"Defensive CM":{"Defensive duels per 90":4,"Defensive duels won, %":4,"PAdj Interceptions":3},"Ball Carrier CM":{"Dribbles per 90":4,"Progressive runs per 90":3}},
    "ATT":{"Goal Threat":{"xG per 90":3,"Non-penalty goals per 90":3,"Shots per 90":2,"Touches in box per 90":2},"Playmaker":{"xA per 90":3,"Key passes per 90":1,"Passes to penalty area per 90":2},"Ball Carrier":{"Dribbles per 90":4,"Progressive runs per 90":3}},
    "GK":{"Shot Stopper":{"Save rate, %":1,"Prevented goals per 90":3},"Ball Playing GK":{"Accurate passes, %":3,"Accurate long passes, %":2},"Sweeper GK":{"Exits per 90":1}},
}
ROLES["ST"]=ROLES["CF"]

def bar_col(pct):
    t=max(0,min(1,pct/100))
    def li(a,b,t): return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))
    r,g,b=li(TAB_RED,TAB_GOLD,t/0.5) if t<=0.5 else li(TAB_GOLD,TAB_GREEN,(t-0.5)/0.5)
    return f"rgb({r},{g},{b})"

def flag_url(country):
    CC={"ghana":"gh","england":"eng","scotland":"sct","wales":"wls","ireland":"ie","france":"fr","germany":"de","spain":"es","italy":"it","portugal":"pt","netherlands":"nl","belgium":"be","brazil":"br","argentina":"ar","nigeria":"ng","senegal":"sn","ivory coast":"ci","cameroon":"cm","morocco":"ma","egypt":"eg","usa":"us","mexico":"mx","japan":"jp","south korea":"kr","australia":"au","croatia":"hr","czech":"cz","poland":"pl","denmark":"dk","sweden":"se","norway":"no","switzerland":"ch","austria":"at","turkey":"tr","ukraine":"ua","russia":"ru","serbia":"rs","romania":"ro","greece":"gr","algeria":"dz","colombia":"co","chile":"cl","uruguay":"uy","ecuador":"ec","paraguay":"py","peru":"pe","venezuela":"ve","ghana":"gh"}
    SP={"eng":"1f3f4-e0067-e0062-e0065-e006e-e0067-e007f","sct":"1f3f4-e0067-e0062-e0073-e0063-e0074-e007f","wls":"1f3f4-e0067-e0062-e0077-e006c-e0073-e007f"}
    n=unicodedata.normalize("NFKD",str(country)).encode("ascii","ignore").decode().strip().lower()
    cc=CC.get(n,"")
    if not cc: return ""
    if cc in SP: return f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/svg/{SP[cc]}.svg"
    b=0x1F1E6; code=f"{b+(ord(cc[0].upper())-65):x}-{b+(ord(cc[1].upper())-65):x}"
    return f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/svg/{code}.svg"

def img_b64(url):
    try:
        r=requests.get(url,timeout=8); r.raise_for_status()
        m=r.headers.get("Content-Type","image/png").split(";")[0].strip()
        return f"data:{m};base64,{base64.b64encode(r.content).decode()}"
    except: return ""

def stars(n,total=5):
    out=""
    for i in range(total):
        if i<int(n): out+='<span style="color:#f6c90e;">★</span>'
        elif i==int(n) and n%1>=0.5: out+='<span style="color:#f6c90e;font-size:14px;">½</span>'
        else: out+='<span style="color:#2a3450;">★</span>'
    return out

def best_role(row,pool,pk):
    rb=ROLES.get(pk,ROLES["CF"]); best_s,best_n=0.0,""
    for rn,mets in rb.items():
        ws,wt=0.0,0.0
        for m,w in mets.items():
            if m not in pool.columns or m not in row.index: continue
            p=pd.to_numeric(pool[m],errors="coerce").dropna()
            v=pd.to_numeric(row.get(m,np.nan),errors="coerce")
            if pd.isna(v) or p.empty: continue
            ws+=float((p<=v).mean()*100)*w; wt+=w
        if wt>0 and ws/wt>best_s: best_s=ws/wt; best_n=rn
    return best_n, round(best_s)

@st.cache_data(show_spinner=False)
def load_seasons():
    dfs={}
    for p in sorted(Path.cwd().glob("*.csv")):
        try:
            df=pd.read_csv(str(p),low_memory=False)
            if "Wyscout ID" not in df.columns or "Season" not in df.columns: continue
            def norm(s):
                s=str(s).strip()
                if "-" in s: return s
                try: y=int(float(s)); return f"{y-1}-{str(y)[2:]}"
                except: return s
            df["Season"]=df["Season"].apply(norm)
            for season in df["Season"].dropna().unique():
                chunk=df[df["Season"]==season].copy()
                dfs[season]=pd.concat([dfs[season],chunk],ignore_index=True) if season in dfs else chunk
        except: pass
    return dfs

def career_history(wid,dfs,pk):
    if not wid or not dfs: return []
    rows=[]
    for season,df in dfs.items():
        df["Wyscout ID"]=pd.to_numeric(df["Wyscout ID"],errors="coerce")
        m=df[df["Wyscout ID"]==int(wid)]
        if m.empty: continue
        row=m.iloc[0]; lg=str(row.get("League",""))
        pool=df[df["League"]==lg] if lg else df
        pk2=POS_KEY.get(str(row.get("Position","")).split(",")[0].strip().upper(),pk)
        rn,rs=best_role(row,pool,pk2)
        def s(c,dp=1):
            v=row.get(c,"")
            try: v=float(v); return str(int(v)) if v==int(v) else f"{v:.{dp}f}"
            except: return str(v) if v else ""
        rows.append({"season":season,"team":str(row.get("Team","")),"league":lg,"apps":s("Matches played"),"mins":s("Minutes played"),"goals":s("Goals"),"assists":s("Assists"),"xg":s("xG"),"xa":s("xA"),"best_role":rn,"best_role_score":rs})
    rows.sort(key=lambda r:r["season"])
    return rows

def build_html(cfg,df_league):
    club=cfg.get("club_color","#1a3a6b")
    pb=cfg.get("photo_b64",""); bb=cfg.get("badge_b64",""); posb=cfg.get("pos_b64","")
    fl=flag_url(cfg.get("nationality","")); flb=img_b64(fl) if fl else ""

    # bars
    pt=str(cfg.get("position_token","CF")).strip().upper()
    fk=POS_KEY.get(pt,"CF"); secs=FEATURE_F.get(fk,FEATURE_F["CF"])
    prow=None
    if df_league is not None and cfg.get("player_name"):
        m=df_league[df_league["Player"].astype(str).str.lower()==cfg["player_name"].strip().lower()]
        if not m.empty: prow=m.iloc[0]
    bars=""
    for sname,mets in secs.items():
        mets=[x for x in mets if x]
        if not mets: continue
        bars+=f'<div class="sh">{sname}</div>'
        for met in mets:
            pct=50.0; rv=""
            if prow is not None and df_league is not None and met in df_league.columns and met in prow.index:
                pool=pd.to_numeric(df_league[met],errors="coerce").dropna()
                v=pd.to_numeric(prow.get(met,np.nan),errors="coerce")
                if pd.notna(v) and not pool.empty:
                    pct=float((pool<=v).mean()*100)
                    rv=f"{int(round(v))}%" if "%" in met else (str(int(v)) if v==int(v) else f"{v:.2f}")
            bc=bar_col(pct)
            sh=met.replace(" per 90","").replace(", %"," %").replace("Accurate ","Acc ").replace("Successful ","Succ ")
            bars+=f'<div class="br"><div class="bl">{sh}</div><div class="bw"><div class="bt"><div class="bf" style="width:{pct:.1f}%;background:{bc};"><span class="bv">{rv}</span></div></div><div class="bm"></div></div></div>'

    ticks="".join(f'<span style="position:absolute;left:{p}%;transform:translateX(-50%);font-size:7px;color:#4b5563;">{p}%</span>' for p in range(0,101,10))

    # trend
    td=cfg.get("trend_data",[]); tsvg=""
    if len(td)>=2:
        W,H=220,65; sc=[d[1] for d in td]; mn,mx=min(sc)-5,max(sc)+5
        def tx(i): return int(i*(W-20)/(len(td)-1)+10)
        def ty(s): return int(H-8-(s-mn)/(max(mx-mn,1))*(H-18))
        pts=" ".join(f"{tx(i)},{ty(s)}" for i,(_,s) in enumerate(td))
        dots=""
        for i,(season,score) in enumerate(td):
            x,y=tx(i),ty(score)
            dots+=f'<circle cx="{x}" cy="{y}" r="5" fill="#00cadc"/><text x="{x}" y="{y-9}" text-anchor="middle" fill="#fff" font-size="11" font-weight="800" font-family="Montserrat">{score}</text><text x="{x}" y="{H+12}" text-anchor="middle" fill="#6b7280" font-size="9" font-family="Montserrat">{season}</text>'
        tsvg=f'<svg width="{W}" height="{H+18}" xmlns="http://www.w3.org/2000/svg"><polyline points="{pts}" fill="none" stroke="#00cadc" stroke-width="2.5"/>{dots}</svg>'

    # roles
    roles_h=""
    for rn,rs in cfg.get("roles",[])[:3]:
        sc=int(rs); bc=bar_col(sc); fg="#000" if sc>45 else "#fff"
        roles_h+=f'<div class="rp"><span class="rn">{rn}</span><span class="rs" style="background:{bc};color:{fg};">{sc}</span></div>'

    # physical
    dc={5:"#22c55e",4:"#4ade80",3:"#facc15",2:"#f97316",1:"#ef4444"}; ph_h=""
    for attr,dots in cfg.get("physical",{"Pace":4,"Power":3,"Fitness":3}).items():
        dr="".join(f'<span class="dot" style="background:{dc.get(dots,"#22c55e")};"></span>' if i<dots else '<span class="dot empty"></span>' for i in range(5))
        ph_h+=f'<div class="pr"><span class="pl">{attr}</span><span class="dots">{dr}</span></div>'

    # form
    fm={"W":"#22c55e","D":"#f59e0b","L":"#ef4444","G":"#22c55e","A":"#f59e0b","P":"#ef4444"}
    form_h="".join(f'<span class="fb" style="background:{fm.get(r.upper(),"#4b5563")};"></span>' for r in cfg.get("form",[])[:5])

    try: rv2=float(cfg.get("avg_rating","0")); rc="#ef4444" if rv2<6.5 else "#f59e0b" if rv2<7.0 else "#22c55e"
    except: rc="#4b5563"

    photo_h=f'<img src="{pb}" class="pp">' if pb else '<div class="pp ph">📷</div>'
    badge_h=f'<img src="{bb}" class="tb">' if bb else ""
    pos_h  =f'<img src="{posb}" class="pd">' if posb else ""
    flag_h =f'<img src="{flb}" class="fl">' if flb else ""
    a5=cfg.get("avg_rating_5","")
    a5h=f'<div style="font-size:9px;color:#9ca3af;margin-top:6px;">⭐ {a5} &nbsp; Last 5 Avg Rating</div>' if a5 else ""

    sstats="".join(f'<div class="ss"><span class="ssl">{l}</span><span class="ssv">{v}</span></div>'
        for l,v in [("Apps",cfg.get("apps","")),("Gls",cfg.get("goals","")),("Asts",cfg.get("assists","")),("xG",cfg.get("xg","")),("xA",cfg.get("xa","")),("Mins",cfg.get("mins",""))])
    sstats+=f'<div class="ss"><span class="ssl">Av.Rat</span><span style="background:{rc};color:#fff;font-size:11px;font-weight:800;padding:1px 7px;border-radius:3px;">{cfg.get("avg_rating","")}</span></div>'

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{width:1920px;height:1080px;overflow:hidden;background:#0a0f1c;font-family:'Montserrat',sans-serif;color:#fff;}}
.hdr{{position:absolute;top:0;left:0;right:0;height:305px;background:linear-gradient(to right,{club} 0%,#0a0f1c 58%);display:flex;align-items:flex-start;padding:20px 16px 0;gap:18px;}}
.pp{{width:258px;height:258px;object-fit:cover;border-radius:4px;flex-shrink:0;}}
.ph{{width:258px;height:258px;background:#111827;display:flex;align-items:center;justify-content:center;font-size:56px;border-radius:4px;flex-shrink:0;}}
.hi{{flex:1;padding-top:2px;}}
.pn{{font-size:42px;font-weight:900;line-height:1.1;letter-spacing:-.5px;}}
.pf{{font-size:19px;font-weight:600;color:#d1d5db;margin-top:4px;}}
.ar{{display:flex;align-items:center;gap:7px;margin-top:7px;font-size:14px;color:#d1d5db;}}
.fl{{height:19px;width:auto;border-radius:2px;}}
.tbl{{display:flex;align-items:flex-start;gap:12px;margin-top:16px;}}
.tb{{width:70px;height:70px;object-fit:contain;}}
.ti{{display:flex;flex-direction:column;gap:2px;}}
.tn{{font-size:18px;font-weight:800;}}
.tl{{font-size:13px;color:#9ca3af;}}
.tim{{font-size:11px;color:#6b7280;}}
.sb{{margin-left:auto;display:flex;flex-direction:column;gap:5px;padding-top:2px;}}
.sr{{display:flex;gap:6px;font-size:13px;}}
.srl{{color:#9ca3af;width:70px;}}
.srv{{color:#fff;font-weight:700;}}
.pd{{position:absolute;top:20px;right:18px;width:155px;height:155px;object-fit:contain;}}
.nav{{position:absolute;top:195px;left:282px;display:flex;gap:28px;font-size:11px;color:#6b7280;}}
.srow{{position:absolute;top:305px;left:0;width:900px;height:30px;background:#0d1117;display:flex;align-items:center;padding:0 10px;gap:0;}}
.sl{{font-size:12px;font-weight:800;color:#ff66c4;margin-right:10px;white-space:nowrap;}}
.ss{{display:flex;flex-direction:column;align-items:center;min-width:75px;}}
.ssl{{font-size:8px;color:#6b7280;}}
.ssv{{font-size:11px;font-weight:700;}}
.vd{{position:absolute;top:305px;bottom:0;width:1px;background:#1a2540;}}
.bp{{position:absolute;top:335px;left:0;width:895px;padding:4px 0;}}
.sh{{font-size:12px;font-weight:800;color:#fff;padding:4px 8px 2px;}}
.br{{display:flex;align-items:center;padding:1px 5px;height:13px;}}
.bl{{font-size:7.5px;color:#e8eef8;width:152px;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.bw{{flex:1;position:relative;height:10px;}}
.bt{{width:100%;height:10px;background:#1a2540;border-radius:2px;overflow:hidden;position:relative;}}
.bf{{height:100%;border-radius:2px;position:relative;}}
.bv{{position:absolute;left:3px;top:50%;transform:translateY(-50%);font-size:7px;font-weight:700;color:#0a0a0a;white-space:nowrap;}}
.bm{{position:absolute;left:50%;top:0;width:1px;height:10px;background:rgba(255,255,255,.45);}}
.np{{position:absolute;top:335px;left:908px;width:248px;padding:7px 10px;}}
.bul{{display:flex;gap:5px;margin-bottom:12px;}}
.bd{{color:#ff66c4;font-size:12px;flex-shrink:0;line-height:1.5;}}
.bc{{font-size:10.5px;line-height:1.55;color:#e8eef8;}}
.blb{{color:#ff66c4;font-weight:700;}}
.lvl{{margin-top:10px;}}
.lt{{font-size:11px;font-weight:800;color:#fff;margin-bottom:4px;}}
.lr{{display:flex;align-items:center;gap:7px;}}
.lx{{font-size:9px;color:#9ca3af;}}
.rp2{{position:absolute;top:305px;left:1168px;right:0;padding:12px 14px;}}
.ph2{{font-size:10px;font-weight:900;color:#fff;letter-spacing:.06em;margin-bottom:8px;}}
.rp{{display:flex;align-items:center;justify-content:space-between;background:#111827;border-radius:7px;padding:5px 8px;margin-bottom:5px;width:196px;}}
.rn{{font-size:9.5px;color:#d1d5db;}}
.rs{{font-size:10px;font-weight:800;padding:2px 7px;border-radius:4px;min-width:28px;text-align:center;}}
.pr{{display:flex;align-items:center;gap:7px;margin-bottom:4px;}}
.pl{{font-size:10px;color:#9ca3af;width:50px;}}
.dots{{display:flex;gap:3px;}}
.dot{{width:13px;height:13px;border-radius:50%;display:inline-block;}}
.dot.empty{{background:#1a2540;}}
.fb{{width:24px;height:24px;border-radius:3px;display:inline-block;}}
.form-row{{display:flex;gap:4px;margin-top:4px;}}
</style></head><body>
<div class="hdr">
  {photo_h}
  <div class="hi">
    <div class="pn">{cfg.get('player_name','')}</div>
    <div class="pf">{cfg.get('position_label','')} &nbsp; {cfg.get('foot','')}</div>
    <div class="ar">{flag_h}<span>{cfg.get('age','')} years old</span><span style="color:#374151;">·</span><span>{cfg.get('dob','')}</span></div>
    <div class="tbl" style="margin-top:16px;">{badge_h}<div class="ti"><div class="tn">{cfg.get('team','')}</div><div class="tl">{cfg.get('league','')}</div><div class="tim">{cfg.get('importance','')}</div></div></div>
  </div>
  <div class="sb">
    <div class="sr"><span class="srl">Height:</span><span class="srv">{cfg.get('height','')}</span></div>
    <div class="sr"><span class="srl">Value:</span><span class="srv">{cfg.get('value','')}</span></div>
    <div class="sr"><span class="srl">Contract:</span><span class="srv">{cfg.get('contract','')}</span></div>
  </div>
</div>
{pos_h}
<div class="nav"><span>Profile ▸</span><span>Performance ▾</span><span>Similar Players ▾</span><span>Club Fit ▾</span><span>Video ▾</span><span>Compare ▾</span></div>
<div class="srow"><span class="sl">Season Stats</span>{sstats}</div>
<div class="vd" style="left:900px;"></div>
<div class="vd" style="left:1162px;"></div>
<div class="bp">
{bars}
<div style="position:relative;height:14px;margin:2px 5px 0 157px;">
  <div style="position:relative;height:14px;">{ticks}</div>
</div>
<div style="text-align:center;font-size:8px;color:#4b5563;padding-top:2px;margin-left:157px;">Percentile Rank</div>
</div>
<div class="np">
  <div class="bul"><span class="bd">•</span><div class="bc"><span class="blb">Key Attributes: </span>{cfg.get('key_attributes','')}</div></div>
  <div class="bul"><span class="bd">•</span><div class="bc"><span class="blb">Development Areas: </span>{cfg.get('dev_areas','')}</div></div>
  <div class="bul"><span class="bd">•</span><div class="bc"><span class="blb">View: </span>{cfg.get('view','')}</div></div>
  <div class="lvl" style="margin-top:16px;"><div class="lt">CURRENT LEVEL</div><div class="lr"><span style="font-size:18px;">{stars(cfg.get('current_stars',3))}</span><span class="lx">{cfg.get('current_level','')}</span></div></div>
  <div class="lvl" style="margin-top:10px;"><div class="lt">POTENTIAL LEVEL</div><div class="lr"><span style="font-size:18px;">{stars(cfg.get('potential_stars',4))}</span><span class="lx">{cfg.get('potential_level','')}</span></div></div>
</div>
<div class="rp2">
  <div class="ph2">BEST ROLE</div>
  {roles_h}
  {'<div style="margin-top:12px;"><div class="ph2">PERFORMANCE TREND</div>'+tsvg+'</div>' if tsvg else ''}
  <div style="margin-top:12px;"><div class="ph2">PHYSICAL</div>{ph_h}</div>
  <div style="margin-top:12px;"><div class="ph2">FORM</div><div class="form-row">{form_h}</div>{a5h}</div>
</div>
</body></html>"""

def render_png(html):
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            br=p.chromium.launch(args=["--no-sandbox","--disable-dev-shm-usage"])
            pg=br.new_page(viewport={"width":1920,"height":1080})
            pg.set_content(html,wait_until="networkidle")
            png=pg.screenshot(full_page=False)
            br.close()
        return png
    except Exception as e:
        return None

# ── UI ────────────────────────────────────────────────────────────────────────
st.title("🃏 Scouting Card Generator")
st.caption("1920×1080 PNG · HTML/CSS rendered via Playwright")

with st.sidebar:
    st.markdown("## 📁 Data")
    csvs=sorted(Path.cwd().glob("*.csv"),key=lambda f:f.stat().st_mtime,reverse=True)
    csv_names=[f.name for f in csvs]
    if csv_names:
        sel=st.selectbox("Primary CSV",csv_names,index=0)
        up=st.file_uploader("Or upload",type="csv")
    else:
        sel=None; up=st.file_uploader("Upload CSV",type="csv")
    st.caption("Career history loads from all CSVs in repo folder")

@st.cache_data(show_spinner=False)
def lcsv(path): return pd.read_csv(path,low_memory=False)
@st.cache_data(show_spinner=False)
def lbytes(data): return pd.read_csv(io.BytesIO(data),low_memory=False)

df=lbytes(up.getvalue()) if up else (lcsv(str(Path.cwd()/sel)) if sel else None)

cf,cp=st.columns([1,1])
with cf:
    st.markdown("### Player")
    a,b=st.columns(2)
    player_name=a.text_input("Player name","Prince Adu"); team=b.text_input("Team","Viktoria Plzen")
    a,b=st.columns(2)
    league=a.text_input("League","Chance Liga"); pos_label=b.text_input("Position label","Center Forward (ST)")
    a,b,c=st.columns(3)
    age=a.text_input("Age","22"); dob=b.text_input("DOB","23/9/2003"); foot=c.selectbox("Foot",["Right","Left","Both"])
    a,b=st.columns(2)
    nat=a.text_input("Nationality","Ghana"); imp=b.text_input("Importance","Important Player")
    a,b,c=st.columns(3)
    ht=a.text_input("Height","5'11"); val=b.text_input("Value","€3m"); con=c.text_input("Contract","2027")

    st.markdown("### Club")
    a,b=st.columns(2)
    club_col=a.text_input("Club hex","#1a3a6b"); badge_url=b.text_input("Badge URL","")

    st.markdown("### Season Stats")
    cols=st.columns(7)
    apps=cols[0].text_input("Apps","13(8)"); gls=cols[1].text_input("Gls","6"); asts=cols[2].text_input("Asts","1")
    xg=cols[3].text_input("xG","5.8"); xa=cols[4].text_input("xA","1.7"); mins=cols[5].text_input("Mins","1,320"); rat=cols[6].text_input("Rat","6.9")

    st.markdown("### Images")
    photo_url=st.text_input("Photo URL (blank=auto)","")
    pos_up=st.file_uploader("Position diagram",type=["png","jpg","webp"])

    st.markdown("### Position")
    pos_tok=st.selectbox("Token",["CF","ST","CB","LCB","RCB","LB","RB","LWB","RWB","DMF","LDMF","RDMF","LCMF","RCMF","AMF","LAMF","RAMF","LW","RW","LWF","RWF","GK"])

    st.markdown("### Notes")
    ka=st.text_area("Key Attributes","Acceleration, pace, taking contact, penalty-box instinct & movement, unpredictability, ball control, dribbling, channel running",height=68)
    da=st.text_area("Development Areas","Finishing, availability, consistency",height=50)
    vw=st.text_area("View","Fitness / injuries have stalled initial excellent progress and struggles for consistent run of form but natural talent and ability. Differential skillset, not quite target man but suits.",height=88)

    st.markdown("### Roles")
    rls=[]
    for i in range(3):
        a,b=st.columns([3,1])
        rn=a.text_input(f"Role {i+1}",["Target Man ST","Goal Threat ST","Link-Up ST"][i],key=f"rn{i}")
        rs=b.text_input("Score",["49","79","78"][i],key=f"rs{i}")
        if rn:
            try: rls.append((rn,int(rs)))
            except: rls.append((rn,0))

    st.markdown("### Level")
    a,b=st.columns(2)
    cs=a.slider("Current ★",0.0,5.0,3.5,0.5); ps=b.slider("Potential ★",0.0,5.0,4.0,0.5)
    cl=a.text_input("Current label","Very Good Champ ST"); pl=b.text_input("Potential label","Good Top 5 EU League ST")

    st.markdown("### Trend")
    tmode=st.radio("Source",["Auto (Wyscout ID)","Manual"],horizontal=True)
    wid=st.text_input("Wyscout ID","")
    td=[]; cr=[]
    if tmode=="Manual":
        for i in range(5):
            a,b=st.columns(2)
            s=a.text_input(f"Season {i+1}","",key=f"ts{i}"); v=b.text_input("Score","",key=f"tv{i}")
            if s and v:
                try: td.append((s,int(v)))
                except: pass

    st.markdown("### Physical")
    a,b,c=st.columns(3)
    pace=a.slider("Pace",1,5,5); power=b.slider("Power",1,5,4); fit=c.slider("Fitness",1,5,3)

    st.markdown("### Form")
    form_str=st.text_input("Form (WDLWW)","DWLLW"); avg5=st.text_input("Last 5 avg","6.3")

    gen=st.button("🖼 Generate Card",type="primary",use_container_width=True)

with cp:
    st.markdown("### Preview")
    if gen:
        pk=POS_KEY.get(pos_tok,"CF")
        if tmode=="Auto (Wyscout ID)" and wid.strip():
            with st.spinner("Loading career history…"):
                sdfs=load_seasons(); cr=career_history(wid.strip(),sdfs,pk)
            td=[(r["season"],r["best_role_score"]) for r in cr if r["best_role_score"]>0]

        df_lg=None
        if df is not None:
            m=df["League"].astype(str).str.lower()==league.strip().lower()
            df_lg=df[m].copy() if m.any() else df.copy()

        with st.spinner("Fetching images…"):
            pb=img_b64(photo_url) if photo_url.strip() else ""
            if not pb:
                try:
                    from photo_utils import get_player_photo_url
                    u=get_player_photo_url(player_name,team)
                    if u: pb=img_b64(u)
                except: pass
            bb2=img_b64(badge_url) if badge_url.strip() else ""
            posb=""
            if pos_up:
                from PIL import Image as PI
                img=PI.open(pos_up).convert("RGBA"); buf=io.BytesIO(); img.save(buf,"PNG")
                posb="data:image/png;base64,"+base64.b64encode(buf.getvalue()).decode()

        cfg=dict(player_name=player_name,team=team,league=league,position_label=pos_label,position_token=pos_tok,
                 age=age,dob=dob,foot=foot,nationality=nat,importance=imp,height=ht,value=val,contract=con,
                 club_color=club_col,photo_b64=pb,badge_b64=bb2,pos_b64=posb,
                 apps=apps,goals=gls,assists=asts,xg=xg,xa=xa,mins=mins,avg_rating=rat,
                 key_attributes=ka,dev_areas=da,view=vw,roles=rls,
                 current_stars=cs,current_level=cl,potential_stars=ps,potential_level=pl,
                 trend_data=td,physical={"Pace":pace,"Power":power,"Fitness":fit},
                 form=list(form_str.upper()[:5]),avg_rating_5=avg5)

        with st.spinner("Rendering…"):
            html=build_html(cfg,df_lg); png=render_png(html)

        if png and isinstance(png,bytes):
            st.image(png,use_column_width=True)
            st.download_button("⬇️ Download PNG",data=png,
                file_name=f"{player_name.replace(' ','_')}_card.png",mime="image/png")
        else:
            st.error("Playwright not available. Downloading HTML instead.")
            b64h=base64.b64encode(html.encode()).decode()
            st.markdown(f'<a href="data:text/html;base64,{b64h}" download="card.html">⬇️ Download HTML (open in Chrome)</a>',unsafe_allow_html=True)

        if cr:
            st.markdown("#### Career History")
            cdf=pd.DataFrame(cr)[["season","team","league","apps","mins","goals","assists","xg","xa","best_role","best_role_score"]]
            cdf.columns=["Season","Team","League","Apps","Mins","G","A","xG","xA","Best Role","Score"]
            st.dataframe(cdf,use_container_width=True,hide_index=True)
    else:
        st.info("Fill in the form and click **Generate Card**")
