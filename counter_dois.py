# counter_dois.py
import json
import re
import unicodedata
from collections import defaultdict
from io import BytesIO

import pandas as pd
import matplotlib.pyplot as plt

# =============================
# NORMALIZAÇÃO DE TEXTO
# =============================
def normalizar(texto: str) -> str:
    if not isinstance(texto, str):
        return ""
    # Remove acentos, mantém só “base character” e baixa tudo
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
    return texto.lower()

# Para modo EXATO: tokeniza a string normalizada em “palavras” (\w = letras/dígitos/_ em Unicode)
_WORD_RE = re.compile(r"\w+", re.UNICODE)
def tokenizar(texto: str):
    return _WORD_RE.findall(normalizar(texto))

# =============================
# ARQUIVOS DAS BÍBLIAS
# =============================
VERSOES = {
    "ACF": "acf.json",
    "AA": "aa.json",
    "NVI": "nvi.json",
    "Grego": "el_greek.json",
    "Hebraico": "hebrew.json",
}

# =============================
# MAPA BÍBLICO COMPLETO (PT)
# =============================
MAPA_LIVROS = {
    "gn": "Gênesis", "ex": "Êxodo", "lv": "Levítico", "nm": "Números", "dt": "Deuteronômio",
    "js": "Josué", "jz": "Juízes", "rt": "Rute", "1sm": "1 Samuel", "2sm": "2 Samuel",
    "1rs": "1 Reis", "2rs": "2 Reis", "1cr": "1 Crônicas", "2cr": "2 Crônicas", "ed": "Esdras",
    "ne": "Neemias", "et": "Ester", "jó": "Jó", "sl": "Salmos", "pv": "Provérbios",
    "ec": "Eclesiastes", "ct": "Cantares", "is": "Isaías", "jr": "Jeremias", "lm": "Lamentações",
    "ez": "Ezequiel", "dn": "Daniel", "os": "Oséias", "jl": "Joel", "am": "Amós",
    "ob": "Obadias", "jn": "Jonas", "mq": "Miquéias", "na": "Naum", "hc": "Habacuque",
    "sf": "Sofonias", "ag": "Ageu", "zc": "Zacarias", "ml": "Malaquias",
    "mt": "Mateus", "mc": "Marcos", "lc": "Lucas", "jo": "João", "at": "Atos",
    "rm": "Romanos", "1co": "1 Coríntios", "2co": "2 Coríntios", "gl": "Gálatas", "ef": "Efésios",
    "fp": "Filipenses", "cl": "Colossenses", "1ts": "1 Tessalonicenses", "2ts": "2 Tessalonicenses",
    "1tm": "1 Timóteo", "2tm": "2 Timóteo", "tt": "Tito", "fm": "Filemom", "hb": "Hebreus",
    "tg": "Tiago", "1pe": "1 Pedro", "2pe": "2 Pedro", "1jo": "1 João", "2jo": "2 João",
    "3jo": "3 João", "jd": "Judas", "ap": "Apocalipse",
}
ORDEM = list(MAPA_LIVROS.keys())

# =============================
# MAPA: NOME DO LIVRO HEBRAICO → ABREV PT
# =============================
MAPA_HEB_ABREV = {
    "בראשית": "gn", "שמות": "ex", "ויקרא": "lv", "במדבר": "nm", "דברים": "dt",
    "יהושע": "js", "שופטים": "jz", "רות": "rt", "שמואל א": "1sm", "שמואל ב": "2sm",
    "מלכים א": "1rs", "מלכים ב": "2rs", "דברי הימים א": "1cr", "דברי הימים ב": "2cr",
    "עזרא": "ed", "נחמיה": "ne", "אסתר": "et", "איוב": "jó", "תהלים": "sl",
    "משלי": "pv", "קהלת": "ec", "שיר השירים": "ct", "ישעיהו": "is", "ירמיהו": "jr",
    "איכה": "lm", "יחזקאל": "ez", "דניאל": "dn", "הושע": "os", "יואל": "jl",
    "עמוס": "am", "עבדיה": "ob", "יונה": "jn", "מיכה": "mq", "נחום": "na",
    "חבקוק": "hc", "צפניה": "sf", "חגי": "ag", "זכריה": "zc", "מלאכי": "ml",
}

# =============================
# NÚMEROS HEBRAICOS SIMPLES (capítulos)
# =============================
HEB_NUM = {
    "א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7, "ח": 8, "ט": 9,
    "י": 10, "כ": 20, "ל": 30, "מ": 40, "נ": 50, "ס": 60, "ע": 70, "פ": 80, "צ": 90,
    "ק": 100, "ר": 200, "ש": 300, "ת": 400,
}
def hebraico_para_num(s: str) -> int:
    # Ex.: "יא" = 10 + 1 = 11
    total = 0
    for ch in str(s):
        total += HEB_NUM.get(ch, 0)
    return total if total > 0 else 0

# =============================
# CARREGAMENTO
# =============================
def carregar_versao(path: str):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)

# =============================
# AJUSTE DA ESTRUTURA HEBRAICA
# esperado: lista de dicts {"book": <he>, "chapter": <he>, "verse": <he>, "content": <str>}
# vira: [{"abbrev": "gn", "chapters": [[v1, v2, ...], [..], ...]}]
# =============================
def converter_hebraico(versos):
    livros = defaultdict(lambda: defaultdict(list))
    for v in versos:
        abrev = MAPA_HEB_ABREV.get(v.get("book", ""), None)
        if not abrev:
            continue
        cap = hebraico_para_num(v.get("chapter", ""))
        if cap <= 0:
            continue
        livros[abrev][cap].append(v.get("content", ""))

    resultado = []
    for abrev, caps in livros.items():
        # ordena capítulos numericamente
        ordered = [caps[c] for c in sorted(caps)]
        resultado.append({"abbrev": abrev, "chapters": ordered})
    return resultado

# =============================
# CONTAGEM (agora com modo "substring" OU "exato")
# =============================
def contar_por_livro(biblia, termo: str, modo: str = "substring"):
    termo_n = normalizar(termo)
    contagem = {}

    for livro in biblia:
        total = 0
        for cap in livro["chapters"]:
            for vers in cap:
                if modo == "exato":
                    toks = tokenizar(vers)
                    total += sum(1 for t in toks if t == termo_n)
                else:  # "substring"
                    total += normalizar(vers).count(termo_n)
        contagem[livro["abbrev"]] = total

    return contagem

# =============================
# LISTAR VERSÍCULOS (com modo)
# =============================
def listar_ocorrencias(biblia, termo: str, modo: str = "substring"):
    termo_n = normalizar(termo)
    resultados = []

    for livro in biblia:
        abrev = livro["abbrev"]
        for c_idx, cap in enumerate(livro["chapters"], start=1):
            for v_idx, vers in enumerate(cap, start=1):
                if modo == "exato":
                    toks = tokenizar(vers)
                    if termo_n in toks:
                        resultados.append((abrev, c_idx, v_idx, vers))
                else:  # "substring"
                    if termo_n in normalizar(vers):
                        resultados.append((abrev, c_idx, v_idx, vers))

    return resultados

# =============================
# HEATMAP (importa seaborn apenas aqui)
# =============================
def gerar_heatmap(df: pd.DataFrame, termo: str) -> BytesIO:
    # Import “preguiçoso” para evitar conflitos locais
    import seaborn as sns

    fig, ax = plt.subplots(figsize=(10, max(6, len(df) * 0.18)))
    sns.heatmap(df, annot=False, linewidths=0.3, ax=ax)
    ax.set_title(f"Mapa de calor — '{termo}'", pad=12)
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf

# =============================
# CARREGA TODAS AS VERSÕES AQUI (usado pelo painel)
# =============================
def _carregar_todas():
    biblias_locais = {}
    for nome, path in VERSOES.items():
        data = carregar_versao(path)
        if nome == "Hebraico":
            data = converter_hebraico(data)
        biblias_locais[nome] = data
    return biblias_locais

biblias = _carregar_todas()

# =============================
# CLI opcional
# =============================
if __name__ == "__main__":
    print("Versões carregadas:", list(biblias.keys()))
    while True:
        termo = input("\nDigite a palavra/frase (ou 'sair'): ").strip()
        if termo.lower() == "sair":
            break
        modo = input("Modo ('substring' ou 'exato'): ").strip().lower() or "substring"

        tabela = pd.DataFrame({
            nome: contar_por_livro(biblia, termo, modo)
            for nome, biblia in biblias.items()
        })
        # Ordena pela ordem bíblica; para abreviações desconhecidas, mantém como vier
        tabela = tabela.reindex(ORDEM)
        tabela.index = [MAPA_LIVROS.get(ab, ab.upper()) for ab in tabela.index]
        tabela = tabela.fillna(0).astype(int)

        print("\nRESULTADO:\n")
        print(tabela.to_string())

        print("\nTOTAL GERAL:\n")
        print(tabela.sum())

        ver = input("Listar versículos? (s/n): ").strip().lower()
        if ver == "s":
            for nome, biblia in biblias.items():
                oc = listar_ocorrencias(biblia, termo, modo)
                if not oc:
                    continue
                print(f"\n--- {nome} ({len(oc)}) ---")
                for ab, c, v, texto in oc:
                    livro = MAPA_LIVROS.get(ab, ab.upper())
                    print(f"{livro} {c}:{v} — {texto}")
        print()
