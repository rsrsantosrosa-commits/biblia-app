import streamlit as st
import pandas as pd
from counter_dois import (
    biblias, contar_por_livro, listar_ocorrencias,
    MAPA_LIVROS, ORDEM, normalizar, gerar_heatmap
)

# -----------------------------------
# CONFIGURAÇÃO DO APLICATIVO
# -----------------------------------
st.set_page_config(page_title="Painel Bíblico", layout="wide")
st.title("📖 Painel de Estudo Bíblico Interativo")

st.markdown("""
### Sobre o aplicativo

Este painel permite **pesquisar palavras na Bíblia** em diferentes versões e idiomas.
Atualmente, ele faz buscas em:

- **Português**
  - Almeida Corrigida Fiel (ACF)
  - Almeida Atualizada (AA)
  - Nova Versão Internacional (NVI)
- **Grego (Novo Testamento)** — texto original do NT
- **Hebraico (Antigo Testamento)** — texto original do AT

#### Funcionalidades:
- 🔍 **Busca por texto**:
  - **Raiz:** encontra variações da mesma palavra
  - **Exato:** encontra apenas a palavra isolada

- 📊 **Tabela de contagem por livro e versão**
- 🔥 **Mapa de calor** mostrando onde a palavra se concentra
- 📜 **Lista de versículos encontrados**, organizados por versão


""")


# -----------------------------------
# ENTRADA DO TERMO
# -----------------------------------
termo = st.text_input("Digite a palavra para pesquisar:")

# -----------------------------------
# MODO DE BUSCA (Raiz ou Exato)
# -----------------------------------
modo = st.radio(
    "Modo de busca:",
    ["Raiz (recomendado)", "Exato"],
    help="• Raiz: encontra formas flexionadas (ex: agap → ηγαπησεν)\n• Exato: encontra somente a palavra isolada"
)

modo = "frase" if modo.startswith("Raiz") else "exato"


# Função para destacar texto visualmente
def highlight(texto, termo):
    termo_n = normalizar(termo)
    texto_n = normalizar(texto)
    if termo_n in texto_n:
        return texto.replace(termo, f"**{termo}**")
    return texto


# -----------------------------------
# PROCESSAMENTO
# -----------------------------------
if termo:
    st.subheader(f"Resultado para: **{termo}**  —  Modo: `{modo}`")

    # ------- TABELA DE CONTAGEM -------
    tabela = pd.DataFrame({
        nome: contar_por_livro(biblia, termo, modo)
        for nome, biblia in biblias.items()
    })

    tabela = tabela.reindex(ORDEM)
    tabela.index = [MAPA_LIVROS.get(ab, ab.upper()) for ab in tabela.index]
    tabela = tabela.fillna(0).astype(int)

    st.write("## 📊 Distribuição por Livro e Versão")
    st.dataframe(tabela, use_container_width=True)

    # ------- HEATMAP -------
    st.write("## 🔥 Mapa de Calor")
    img = gerar_heatmap(tabela, termo)
    st.pyplot(img, use_container_width=True)


    # ------- LISTA DE VERSÍCULOS -------
    st.write("## 📜 Versículos encontrados")

    for nome, biblia in biblias.items():
        ocorrencias = listar_ocorrencias(biblia, termo, modo)
        if ocorrencias:
            with st.expander(f"{nome} — {len(ocorrencias)} ocorrência(s)"):
                for ab, c, v, texto in ocorrencias:
                    livro = MAPA_LIVROS.get(ab, ab.upper())
                    st.write(f"**{livro} {c}:{v}** — {highlight(texto, termo)}")


