# counter_dois.py
# ------------------------------------------------------------
# Contador de ocorrências por livro (PT-BR, Grego e Hebraico)
# + função gerar_heatmap usada pelo painel
# ------------------------------------------------------------

import json
import re
import unicodedata
from collections import defaultdict
import pandas as pd
import matplotlib.pyplot as plt


# =============================
# NORMALIZAÇÃO
# =============================
def normalizar(texto: str) -> str:
    if not isinstance(texto, str):
        return ""
    # Normaliza Unicode
    txt = unicodedata.normalize("NFD", texto)
    # Remove marcas (acentos, espíritos, iota subescrita)
    txt = "".join(ch for ch in txt if unicodedata.category(ch) != "Mn")
    txt = txt.lower()
    # grego: sigma final → sigma normal
    txt = txt.replace("ς", "σ")
    return txt


# =============================
# ARQUIVOS
# =============================
VERSOES = {
    "ACF": "acf.json",
    "AA": "aa.json",
    "NVI": "nvi.json",
    "Grego": "el_greek.json",
    "Hebraico": "hebrew.json",
}

# =============================
# MAPA COMPLETO
# =============================
MAPA_LIVROS = {
    "gn":"Gênesis","ex":"Êxodo","lv":"Levítico","nm":"Números","dt":"Deuteronômio",
    "js":"Josué","jz":"Juízes","rt":"Rute","1sm":"1 Samuel","2sm":"2 Samuel",
    "1rs":"1 Reis","2rs":"2 Reis","1cr":"1 Crônicas","2cr":"2 Crônicas","ed":"Esdras",
    "ne":"Neemias","et":"Ester","jó":"Jó","sl":"Salmos","pv":"Provérbios",
    "ec":"Eclesiastes","ct":"Cânticos","is":"Isaías","jr":"Jeremias","lm":"Lamentações",
    "ez":"Ezequiel","dn":"Daniel","os":"Oséias","jl":"Joel","am":"Amós",
    "ob":"Obadias","jn":"Jonas","mq":"Miquéias","na":"Naum","hc":"Habacuque",
    "sf":"Sofonias","ag":"Ageu","zc":"Zacarias","ml":"Malaquias",
    "mt":"Mateus","mc":"Marcos","lc":"Lucas","jo":"João","at":"Atos",
    "rm":"Romanos","1co":"1 Coríntios","2co":"2 Coríntios","gl":"Gálatas","ef":"Efésios",
    "fp":"Filipenses","cl":"Colossenses","1ts":"1 Tessalonicenses","2ts":"2 Tessalonicenses",
    "1tm":"1 Timóteo","2tm":"2 Timóteo","tt":"Tito","fm":"Filemom","hb":"Hebreus",
    "tg":"Tiago","1pe":"1 Pedro","2pe":"2 Pedro","1jo":"1 João","2jo":"2 João",
    "3jo":"3 João","jd":"Judas","ap":"Apocalipse"
}
ORDEM = list(MAPA_LIVROS.keys())

# =============================
# ALIASES PARA UNIFICAR JSONs
# =============================
ALIASES = {
    "1ch":"1cr","2ch":"2cr",
    "1kgs":"1rs","2kgs":"2rs",
    "ezr":"ed",
    "eph":"ef",
    "ps":"sl","psa":"sl","psalms":"sl",
    "prov":"pv","prv":"pv",
    "ecc":"ec","eccl":"ec",
    "act":"at","acts":"at",

    # Correções que faltavam:
    "job": "jó",
    "lk": "lc",
    "mk": "mc",
    "jm": "tg",      # James → Tiago
    "ph": "fp",      # Philippians → Filipenses
    "phm": "fm",     # Philemon → Filemom
    "so": "sf",      # Sophonias → Sofonias
    "re": "ap",      # Revelation → Apocalipse
    "ho": "os",      # Hosea → Oséias
    "hg": "ag",      # Haggai → Ageu
    "hk": "hc",      # Habakkuk → Habacuque
    "mi": "mq",      # Micah → Miquéias
    "zp": "zc",      # Zephaniah → Zacarias (LXX às vezes troca ordem)
}

def canon_abbrev(a: str) -> str:
    if not a:
        return a
    a = normalizar(a).replace(".", "").replace(" ", "")
    return ALIASES.get(a, a)

def nome_completo(a: str) -> str:
    return MAPA_LIVROS.get(a, a)

# =============================
# HEBRAICO
# =============================
MAPA_HEB_ABREV = {
    "בראשית":"gn","שמות":"ex","ויקרא":"lv","במדבר":"nm","דברים":"dt",
    "יהושע":"js","שופטים":"jz","רות":"rt","שמואל א":"1sm","שמואל ב":"2sm",
    "מלכים א":"1rs","מלכים ב":"2rs","דברי הימים א":"1cr","דברי הימים ב":"2cr",
    "עזרא":"ed","נחמיה":"ne","אסתר":"et","איוב":"jó","תהלים":"sl",
    "משלי":"pv","קהלת":"ec","שיר השירים":"ct","ישעיהו":"is","ירמיהו":"jr",
    "איכה":"lm","יחזקאל":"ez","דניאל":"dn","הושע":"os","יואל":"jl",
    "עמוס":"am","עבדיה":"ob","יונה":"jn","מיכה":"mq","נחום":"na",
    "חבקוק":"hc","צפניה":"sf","חגי":"ag","זכריה":"zc","מלאכי":"ml",
}
HEB_NUM = {"א":1,"ב":2,"ג":3,"ד":4,"ה":5,"ו":6,"ז":7,"ח":8,"ט":9,"י":10,
           "כ":20,"ל":30,"מ":40,"נ":50,"ס":60,"ע":70,"פ":80,"צ":90,
           "ק":100,"ר":200,"ש":300,"ת":400}

def hebraico_para_num(s): return sum(HEB_NUM.get(ch,0) for ch in s)

def converter_hebraico(vs):
    livros = defaultdict(lambda: defaultdict(list))
    for v in vs:
        ab = MAPA_HEB_ABREV.get(v["book"])
        if not ab: continue
        c = hebraico_para_num(v["chapter"])
        livros[ab][c].append(v["content"])
    out = []
    for ab, caps in livros.items():
        out.append({"abbrev":ab,"chapters":[caps[c] for c in sorted(caps)]})
    return out

# =============================
# CARREGAMENTO E NORMALIZAÇÃO
# =============================
def carregar_versao(path):
    return json.load(open(path,encoding="utf-8-sig"))

def normalizar_biblia(data):
    out=[]
    for lv in data:
        ab = canon_abbrev(lv.get("abbrev") or lv.get("book"))
        caps = [[str(v) for v in cap] for cap in lv.get("chapters",[])]
        out.append({"abbrev":ab,"chapters":caps})
    return out

def carregar_todas():
    out={}
    for nome,path in VERSOES.items():
        d = carregar_versao(path)
        if nome=="Hebraico": d = converter_hebraico(d)
        d = normalizar_biblia(d)
        out[nome]=d
    return out

biblias = carregar_todas()

# =============================
# CONTAGEM / LISTAGEM
# =============================
def _contar(texto, termo, modo):
    if modo=="exato":
        return len(re.findall(rf"\b{re.escape(termo)}\b", texto))
    return texto.count(termo)

def contar_por_livro(bib, termo, modo="fuzzy"):
    termo = normalizar(termo)
    out={}
    for lv in bib:
        tot=0
        for cap in lv["chapters"]:
            for v in cap:
                tot+=_contar(normalizar(v),termo,modo)
        out[lv["abbrev"]]=tot
    return out

def listar_ocorrencias(biblia, termo, modo="frase"):
    termo_n = normalizar(termo)

    resultados = []
    for livro in biblia:
        abrev = livro["abbrev"]
        for c_idx, cap in enumerate(livro["chapters"], start=1):
            for v_idx, vers in enumerate(cap, start=1):
                texto_n = normalizar(vers)

                if modo == "exato":
                    if f" {termo_n} " in f" {texto_n} ":
                        resultados.append((abrev, c_idx, v_idx, vers))
                else:  # busca por raiz (stem)
                    if termo_n in texto_n:
                        resultados.append((abrev, c_idx, v_idx, vers))
    return resultados


# =============================
# HEATMAP (usado pelo painel)
# =============================
def gerar_heatmap(df, termo):
    import seaborn as sns  # <-- agora importamos só aqui, quando necessário
    plt.figure(figsize=(12,14))
    sns.heatmap(df, annot=True, cmap="YlOrRd")
    fname = f"heatmap_{normalizar(termo)}.png"
    plt.savefig(fname, dpi=300, bbox_inches='tight')
    plt.close()
    return fname


# =============================
# CLI
# =============================
def main():
    while True:
        termo=input("\nDigite a palavra (ou sair): ").strip()
        if normalizar(termo)=="sair": break
        modo=input("Modo (fuzzy/exato): ").strip().lower() or "fuzzy"
        tabela = pd.DataFrame({n:contar_por_livro(b,termo,modo) for n,b in biblias.items()})
        tabela=tabela.reindex(ORDEM).fillna(0).astype(int)
        tabela.index=[MAPA_LIVROS.get(i,i) for i in tabela.index]
        print("\n",tabela,"\n")
        print("TOTAL:\n",tabela.sum())

if __name__=="__main__":
    main()
