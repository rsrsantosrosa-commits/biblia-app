# counter_dois.py
import json
import re
import unicodedata
from collections import defaultdict
from io import BytesIO

import pandas as pd


# =============================
# Normalização de texto
# =============================
def normalizar(texto: str) -> str:
    """Remove acentos/diacríticos e coloca em minúsculas."""
    if not isinstance(texto, str):
        return ""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
    return texto.lower()


# =============================
# Arquivos das Bíblias
# (mantenha estes nomes no mesmo diretório do app)
# =============================
VERSOES = {
    "ACF": "acf.json",
    "AA": "aa.json",
    "NVI": "nvi.json",
    "Grego": "el_greek.json",
    "Hebraico": "hebrew.json",
}


# =============================
# Mapa bíblico (abreviação -> nome)
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
# ordem canônica para reindex
ORDEM = list(MAPA_LIVROS.keys())


# =============================
# Mapeamento: livro em hebraico -> abreviação PT
# (para alinhar com ORDEM/MAPA_LIVROS)
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
# Conversão de “número” hebraico para inteiro (capítulos)
# Aceita strings como י״א, ט״ו, יג, etc.
# =============================
HEB_NUM_VAL = {
    "א":1,"ב":2,"ג":3,"ד":4,"ה":5,"ו":6,"ז":7,"ח":8,"ט":9,"י":10,
    "כ":20,"ל":30,"מ":40,"נ":50,"ס":60,"ע":70,"פ":80,"צ":90,
    "ק":100,"ר":200,"ש":300,"ת":400,
}
HEB_NUM_CLEAN_RE = re.compile(r"[^אבגדהוזחטיכלמנסעפצקרשת]")

def hebraico_para_num(s: str) -> int:
    if not isinstance(s, str):
        return 0
    s = HEB_NUM_CLEAN_RE.sub("", s)  # remove geresh/gershayim e outros sinais
    total = 0
    for ch in s:
        total += HEB_NUM_VAL.get(ch, 0)
    return max(total, 0)


# =============================
# I/O
# =============================
def carregar_versao(path: str):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


# =============================
# Ajuste estrutura do hebraico
# Entrada esperada: lista de dicts com keys: book, chapter, verse, content
# Saída: [{"abbrev": "...", "chapters": [[v1,v2,...],[...], ...]}]
# =============================
def converter_hebraico(versos: list) -> list:
    livros = defaultdict(lambda: defaultdict(list))  # {abrev: {cap: [versos...]}}
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
        # capítulos em ordem crescente, cada um como lista de versos
        ordered = [caps[c] for c in sorted(caps)]
        resultado.append({"abbrev": abrev, "chapters": ordered})
    return resultado


# =============================
# Contagem por livro
# modo = "substring" | "exato"
# =============================
def _count_in_text(text_norm: str, term_norm: str, modo: str) -> int:
    if not term_norm:
        return 0
    if modo == "exato":
        # borda de palavra: sem letras/nums/underscore antes/depois
        pat = re.compile(rf"(?<!\w){re.escape(term_norm)}(?!\w)")
        return len(pat.findall(text_norm))
    # substring (contém)
    return text_norm.count(term_norm)


def contar_por_livro(biblia: list, termo: str, modo: str = "substring") -> dict:
    term_norm = normalizar(termo)
    contagem = {}
    for livro in biblia:
        total = 0
        for cap in livro["chapters"]:
            for vers in cap:
                total += _count_in_text(normalizar(vers), term_norm, modo)
        contagem[livro["abbrev"]] = int(total)
    return contagem


# =============================
# Listar ocorrências (para mostrar os versículos)
# =============================
def listar_ocorrencias(biblia: list, termo: str, modo: str = "substring"):
    term_norm = normalizar(termo)
    resultados = []
    for livro in biblia:
        abrev = livro["abbrev"]
        for c_idx, cap in enumerate(livro["chapters"], start=1):
            for v_idx, vers in enumerate(cap, start=1):
                if _count_in_text(normalizar(vers), term_norm, modo) > 0:
                    resultados.append((abrev, c_idx, v_idx, vers))
    return resultados


# =============================
# Heatmap (matplotlib puro, sem seaborn)
# =============================
def gerar_heatmap(tabela, termo):
    import matplotlib.pyplot as plt
    import seaborn as sns

    # Garantir inteiros para anotar com "d"
    df = tabela.copy().fillna(0).astype(int)

    vmax = int(df.to_numpy().max()) if df.size else 0

    # Altura dinâmica: 0.28 por linha (mín 8) p/ caber os rótulos
    altura = max(8, len(df) * 0.28)
    fig, ax = plt.subplots(figsize=(11, altura))

    sns.heatmap(
        df,
        annot=True,           # <- mostra os números nas células
        fmt="d",              # <- como inteiro
        cmap="YlOrRd",        # <- paleta estável e “quente”
        linewidths=0.5,
        linecolor="#eeeeee",
        cbar=True,
        vmin=0,
        vmax=vmax,
        ax=ax
    )

    ax.set_title(f"Ocorrências de “{termo}” por livro e versão", pad=12)
    ax.set_xlabel("Versões")
    ax.set_ylabel("Livros")

    # Deixar os rótulos menores para não poluir
    ax.tick_params(axis="x", labelrotation=0)
    ax.tick_params(axis="y", labelsize=8)

    fig.tight_layout()
    return fig



# =============================
# Loader das bíblias (para importar no painel)
# =============================
def build_biblias() -> dict:
    result = {}
    for nome, path in VERSOES.items():
        data = carregar_versao(path)
        if nome == "Hebraico":
            data = converter_hebraico(data)
        result[nome] = data
    return result


# objeto pronto para import no painel
biblias = build_biblias()


# =============================
# CLI opcional (terminal)
# =============================
def _main_cli():
    print("Buscador Bíblico — modos: substring | exato")
    while True:
        termo = input("\nDigite a palavra/frase (ou 'sair'): ").strip()
        if termo.lower() == "sair":
            break
        modo = input("Modo (substring/exato) [substring]: ").strip().lower() or "substring"

        tabela = pd.DataFrame({
            nome: contar_por_livro(biblia, termo, modo)
            for nome, biblia in biblias.items()
        })
        # reindex na ordem canônica e traduz índice para nome completo
        tabela = tabela.reindex(ORDEM)
        tabela.index = [MAPA_LIVROS.get(ab, ab.upper()) for ab in tabela.index]
        tabela = tabela.fillna(0).astype(int)

        print("\nRESULTADO:\n")
        print(tabela.to_string())
        print("\nTOTAL GERAL:\n")
        print(tabela.sum())

        # exporta opcional
        try:
            arquivo = f"resultado_{normalizar(termo).replace(' ', '_')}_{modo}.xlsx"
            tabela.to_excel(arquivo)
            print(f"\n📄 Resultado salvo em: {arquivo}\n")
        except Exception as e:
            print(f"(Aviso) Não foi possível salvar o Excel: {e}")


if __name__ == "__main__":
    _main_cli()

