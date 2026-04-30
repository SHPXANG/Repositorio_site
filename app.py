import streamlit as st
import pandas as pd
import requests
import re
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date

# ========================
# FUNÇÕES AUXILIARES
# ========================

def converter_valor(valor):
    """Converte valor da API para float de forma segura."""
    try:
        if isinstance(valor, (int, float)):
            return float(valor)
        valor_str = str(valor).strip()
        valor_str = re.sub(r"[^\d,\.]", "", valor_str)
        if ',' in valor_str and '.' in valor_str:
            valor_str = valor_str.replace('.', '').replace(',', '.')
        elif ',' in valor_str:
            valor_str = valor_str.replace(',', '.')
        return float(valor_str)
    except Exception:
        return 0.0


def formatar_brl(valor):
    """Formata valor numérico para padrão brasileiro R$ X.XXX,XX."""
    return f"R$ {valor:,.2f}".replace('.', '#').replace(',', '.').replace('#', ',')


def coletar_dados(access_token, nome_empresa):
    """Coleta dados paginados da API Maino - Contas a Receber."""
    url_base = "https://api.maino.com.br/api/v2/contas_a_recebers"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    todos_os_dados = []
    pagina = 1

    while True:
        params = {"page": pagina, "per_page": 50}
        try:
            response = requests.get(url_base, headers=headers, params=params, timeout=30)
        except requests.exceptions.RequestException as e:
            st.error(f"Erro de conexão com {nome_empresa}: {e}")
            break

        if response.status_code != 200:
            st.error(f"Erro na coleta de {nome_empresa}: {response.status_code}")
            break

        dados = response.json()
        contas = dados.get("contas") or dados.get("data", {}).get("contas_a_receber", [])

        if not contas:
            break

        for conta in contas:
            valor = converter_valor(conta.get("valor", 0))
            processo_info = conta.get("processo", {}) or {}
            cliente_info = conta.get("cliente", {}) or {}

            # Extrair tags do processo (lista de strings)
            tags = processo_info.get("tags", []) or []
            if isinstance(tags, str):
                tags = [tags]
            tags_str = ", ".join(tags) if tags else ""

            # Verificar se tem tag de câmbio
            tem_cambio = any("câmbio" in t.lower() or "cambio" in t.lower() for t in tags)

            todos_os_dados.append({
                "Número Título": conta.get("numero_titulo", ""),
                "Número Documento": conta.get("numero_fatura", ""),
                "Vencimento": conta.get("data_vencimento", ""),
                "Valor": valor,
                "Data Competência": conta.get("data_competencia", ""),
                "Data Pagamento": conta.get("data_pagamento", ""),
                "Cliente": cliente_info.get("razao_social", ""),
                "Processo": processo_info.get("codigo", ""),
                "Tags": tags_str,
                "Câmbio": tem_cambio,
                "Empresa": nome_empresa,
            })

        pagina += 1

    return pd.DataFrame(todos_os_dados)


# ========================
# CONFIGURAÇÃO DA PÁGINA
# ========================
st.set_page_config(
    page_title="Dashboard Financeiro - Contas a Receber",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ========================
# CSS CUSTOMIZADO
# ========================
st.markdown("""
<style>
    /* ---- Fonte Google ---- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ---- Background ---- */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #161b40 40%, #1a1a2e 100%);
    }

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #12122b 0%, #1a1a3e 100%);
        border-right: 1px solid rgba(255,255,255,0.06);
    }

    /* ---- Cards KPI ---- */
    .kpi-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.07) 0%, rgba(255,255,255,0.03) 100%);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 16px;
        padding: 28px 24px;
        text-align: center;
        transition: transform 0.25s ease, box-shadow 0.25s ease;
        box-shadow: 0 4px 24px rgba(0,0,0,0.25);
    }
    .kpi-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 32px rgba(99,102,241,0.25);
    }
    .kpi-label {
        font-size: 0.82rem;
        font-weight: 600;
        color: rgba(255,255,255,0.50);
        text-transform: uppercase;
        letter-spacing: 1.2px;
        margin-bottom: 8px;
    }
    .kpi-value {
        font-size: 1.85rem;
        font-weight: 800;
        background: linear-gradient(90deg, #6366f1, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .kpi-value-green {
        font-size: 1.85rem;
        font-weight: 800;
        background: linear-gradient(90deg, #22c55e, #10b981);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .kpi-value-amber {
        font-size: 1.85rem;
        font-weight: 800;
        background: linear-gradient(90deg, #f59e0b, #ef4444);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }

    /* ---- Section Headers ---- */
    .section-header {
        font-size: 1.25rem;
        font-weight: 700;
        color: #e2e8f0;
        margin-top: 32px;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 2px solid rgba(99,102,241,0.3);
    }

    /* ---- Divider câmbio ---- */
    .cambio-divider {
        background: linear-gradient(90deg, rgba(245,158,11,0.2), rgba(239,68,68,0.2));
        border: 1px solid rgba(245,158,11,0.3);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }
    .cambio-divider h4 {
        color: #f59e0b;
        margin: 0 0 4px 0;
    }
    .normal-divider {
        background: linear-gradient(90deg, rgba(34,197,94,0.12), rgba(16,185,129,0.12));
        border: 1px solid rgba(34,197,94,0.25);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }
    .normal-divider h4 {
        color: #22c55e;
        margin: 0 0 4px 0;
    }

    /* ---- Tabs ---- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 600;
    }

    /* ---- Hide default Streamlit branding ---- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ---- Dataframe styling ---- */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


# ========================
# AUTENTICAÇÃO (LOGIN)
# ========================
def tela_login():
    """Exibe tela de login e retorna True se autenticado."""
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if st.session_state.autenticado:
        return True

    st.markdown("""
    <div style="display:flex; justify-content:center; align-items:center; min-height:70vh;">
    </div>
    """, unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1, 1.5, 1])
    with col_center:
        st.markdown("""
        <div style="text-align:center; margin-bottom:24px;">
            <h1 style="font-size:2rem; font-weight:800;
                       background: linear-gradient(90deg, #6366f1, #a855f7, #ec4899);
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                🔐 Login
            </h1>
            <p style="color:rgba(255,255,255,0.45); font-size:0.9rem;">Dashboard Financeiro — Contas a Receber</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            usuario = st.text_input("👤 Usuário")
            senha = st.text_input("🔑 Senha", type="password")
            submitted = st.form_submit_button("Entrar", use_container_width=True)

            if submitted:
                user_ok = st.secrets["APP_USER"]
                pass_ok = st.secrets["APP_PASSWORD"]
                if usuario == user_ok and senha == pass_ok:
                    st.session_state.autenticado = True
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos.")

    return False


# Verificar login antes de tudo
if not tela_login():
    st.stop()


# ========================
# EMPRESAS (tokens via Streamlit Secrets)
# ========================
EMPRESAS = [
    {"token": st.secrets["SHOPTAN_TOKEN"], "nome": "Shoptan"},
    {"token": st.secrets["XANGAI_TOKEN"], "nome": "Xangai"},
]


# ========================
# CARREGAMENTO DE DADOS
# ========================
def carregar_todos_dados():
    """Carrega dados de todas as empresas."""
    frames = []
    for empresa in EMPRESAS:
        with st.spinner(f"🔄 Coletando dados de **{empresa['nome']}**..."):
            df = coletar_dados(empresa["token"], empresa["nome"])
            if not df.empty:
                frames.append(df)
    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame()


# Session state para cache
if "df_all" not in st.session_state:
    st.session_state.df_all = carregar_todos_dados()


# ========================
# SIDEBAR
# ========================
with st.sidebar:
    st.markdown("## 📊 Dashboard Financeiro")
    st.markdown("**Contas a Receber — Maino**")
    st.markdown("---")

    # Botão atualizar
    if st.button("🔄 Atualizar Dados", use_container_width=True):
        st.session_state.df_all = carregar_todos_dados()
        st.rerun()

    st.markdown("---")

    # Seleção de empresa
    empresas_disponiveis = ["Todas"] + [e["nome"] for e in EMPRESAS]
    empresa_selecionada = st.selectbox("🏢 Empresa", empresas_disponiveis, index=0)

    st.markdown("---")

    # Botão logout
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

    st.caption("Desenvolvido com ❤️ usando Streamlit")


# ========================
# PROCESSAMENTO DOS DADOS
# ========================
df = st.session_state.df_all.copy()

if df.empty:
    st.warning("⚠️ Nenhum dado foi carregado. Verifique a conexão com a API.")
    st.stop()

# Converter coluna de vencimento para datetime
df["Vencimento_dt"] = pd.to_datetime(df["Vencimento"], errors="coerce")
df["Data Pagamento_dt"] = pd.to_datetime(df["Data Pagamento"], errors="coerce")

# Filtrar apenas em aberto (sem data de pagamento)
df_aberto = df[df["Data Pagamento_dt"].isna()].copy()

# Filtrar por empresa
if empresa_selecionada != "Todas":
    df_aberto = df_aberto[df_aberto["Empresa"] == empresa_selecionada]

# Sem filtro de data — mostra todos em aberto
df_filtrado = df_aberto.copy()


# ========================
# TÍTULO PRINCIPAL
# ========================
st.markdown("""
<div style="text-align:center; padding: 10px 0 24px 0;">
    <h1 style="font-size:2.2rem; font-weight:800; 
               background: linear-gradient(90deg, #6366f1, #a855f7, #ec4899);
               -webkit-background-clip: text; -webkit-text-fill-color: transparent;
               margin-bottom:4px;">
        Dashboard Financeiro — Contas a Receber
    </h1>
    <p style="color: rgba(255,255,255,0.45); font-size:0.95rem;">
        Monitoramento em tempo real dos boletos em aberto
    </p>
</div>
""", unsafe_allow_html=True)


# ========================
# CARDS KPI
# ========================
total_valor = df_filtrado["Valor"].sum()
total_qtd = len(df_filtrado)

# Calcular ticket médio
ticket_medio = total_valor / total_qtd if total_qtd > 0 else 0

# Vencidos
hoje = pd.Timestamp(date.today())
vencidos = df_filtrado[df_filtrado["Vencimento_dt"] < hoje]
total_vencidos = len(vencidos)
valor_vencido = vencidos["Valor"].sum()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">💰 Valor Total em Aberto</div>
        <div class="kpi-value">{formatar_brl(total_valor)}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">🧾 Quantidade em Aberto</div>
        <div class="kpi-value-green">{total_qtd}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">📊 Ticket Médio</div>
        <div class="kpi-value">{formatar_brl(ticket_medio)}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">⚠️ Vencidos ({total_vencidos})</div>
        <div class="kpi-value-amber">{formatar_brl(valor_vencido)}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ========================
# GRÁFICO DE BARRAS POR PROCESSO
# ========================
if not df_filtrado.empty:
    # Verificar se é Xangai (ou "Todas" com dados da Xangai)
    tem_xangai = "Xangai" in df_filtrado["Empresa"].unique()

    if tem_xangai and (empresa_selecionada == "Xangai" or empresa_selecionada == "Todas"):
        # ---- SEÇÃO XANGAI COM SEPARAÇÃO CÂMBIO ----
        st.markdown('<div class="section-header">📊 Valor por Processo — Xangai (Câmbio vs Normal)</div>', unsafe_allow_html=True)

        df_xangai = df_filtrado[df_filtrado["Empresa"] == "Xangai"].copy()

        if not df_xangai.empty:
            # Separar câmbio e normal
            df_cambio = df_xangai[df_xangai["Câmbio"] == True].copy()
            df_normal = df_xangai[df_xangai["Câmbio"] == False].copy()

            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                st.markdown("""
                <div class="cambio-divider">
                    <h4>💱 Com Tag de Câmbio</h4>
                </div>
                """, unsafe_allow_html=True)

                if not df_cambio.empty:
                    cambio_proc = df_cambio.groupby("Processo")["Valor"].sum().reset_index()
                    cambio_proc = cambio_proc.sort_values("Valor", ascending=False)

                    fig_cambio = px.bar(
                        cambio_proc,
                        x="Processo",
                        y="Valor",
                        color_discrete_sequence=["#f59e0b"],
                        text_auto='.2s',
                    )
                    fig_cambio.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#e2e8f0", family="Inter"),
                        xaxis=dict(title="", tickangle=-45, gridcolor="rgba(255,255,255,0.05)"),
                        yaxis=dict(title="Valor (R$)", gridcolor="rgba(255,255,255,0.05)"),
                        margin=dict(l=20, r=20, t=20, b=80),
                        height=420,
                    )
                    fig_cambio.update_traces(
                        marker_line_width=0,
                        marker_cornerradius=6,
                        textposition="outside",
                        textfont_size=11,
                    )
                    st.plotly_chart(fig_cambio, use_container_width=True)

                    st.markdown(f"""
                    <div style="text-align:center; color:rgba(255,255,255,0.5); font-size:0.85rem;">
                        {len(df_cambio)} boletos • {formatar_brl(df_cambio['Valor'].sum())}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("Nenhum boleto com tag de câmbio encontrado.")

            with col_chart2:
                st.markdown("""
                <div class="normal-divider">
                    <h4>📋 Sem Tag de Câmbio</h4>
                </div>
                """, unsafe_allow_html=True)

                if not df_normal.empty:
                    normal_proc = df_normal.groupby("Processo")["Valor"].sum().reset_index()
                    normal_proc = normal_proc.sort_values("Valor", ascending=False)

                    fig_normal = px.bar(
                        normal_proc,
                        x="Processo",
                        y="Valor",
                        color_discrete_sequence=["#22c55e"],
                        text_auto='.2s',
                    )
                    fig_normal.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#e2e8f0", family="Inter"),
                        xaxis=dict(title="", tickangle=-45, gridcolor="rgba(255,255,255,0.05)"),
                        yaxis=dict(title="Valor (R$)", gridcolor="rgba(255,255,255,0.05)"),
                        margin=dict(l=20, r=20, t=20, b=80),
                        height=420,
                    )
                    fig_normal.update_traces(
                        marker_line_width=0,
                        marker_cornerradius=6,
                        textposition="outside",
                        textfont_size=11,
                    )
                    st.plotly_chart(fig_normal, use_container_width=True)

                    st.markdown(f"""
                    <div style="text-align:center; color:rgba(255,255,255,0.5); font-size:0.85rem;">
                        {len(df_normal)} boletos • {formatar_brl(df_normal['Valor'].sum())}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("Nenhum boleto sem tag de câmbio encontrado.")

        # Se "Todas", também mostrar Shoptan separado
        if empresa_selecionada == "Todas":
            df_shoptan = df_filtrado[df_filtrado["Empresa"] == "Shoptan"]
            if not df_shoptan.empty:
                st.markdown('<div class="section-header">📊 Valor por Processo — Shoptan</div>', unsafe_allow_html=True)

                shoptan_proc = df_shoptan.groupby("Processo")["Valor"].sum().reset_index()
                shoptan_proc = shoptan_proc.sort_values("Valor", ascending=False)

                fig_shoptan = px.bar(
                    shoptan_proc,
                    x="Processo",
                    y="Valor",
                    color_discrete_sequence=["#6366f1"],
                    text_auto='.2s',
                )
                fig_shoptan.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e2e8f0", family="Inter"),
                    xaxis=dict(title="Processo", tickangle=-45, gridcolor="rgba(255,255,255,0.05)"),
                    yaxis=dict(title="Valor (R$)", gridcolor="rgba(255,255,255,0.05)"),
                    margin=dict(l=20, r=20, t=20, b=80),
                    height=450,
                )
                fig_shoptan.update_traces(
                    marker_line_width=0,
                    marker_cornerradius=6,
                    textposition="outside",
                    textfont_size=11,
                )
                st.plotly_chart(fig_shoptan, use_container_width=True)

    elif empresa_selecionada == "Shoptan":
        # ---- SEÇÃO SHOPTAN ----
        st.markdown('<div class="section-header">📊 Valor por Processo — Shoptan</div>', unsafe_allow_html=True)

        proc_data = df_filtrado.groupby("Processo")["Valor"].sum().reset_index()
        proc_data = proc_data.sort_values("Valor", ascending=False)

        fig = px.bar(
            proc_data,
            x="Processo",
            y="Valor",
            color_discrete_sequence=["#6366f1"],
            text_auto='.2s',
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0", family="Inter"),
            xaxis=dict(title="Processo", tickangle=-45, gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(title="Valor (R$)", gridcolor="rgba(255,255,255,0.05)"),
            margin=dict(l=20, r=20, t=20, b=80),
            height=450,
        )
        fig.update_traces(
            marker_line_width=0,
            marker_cornerradius=6,
            textposition="outside",
            textfont_size=11,
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        # ---- GRÁFICO GERAL (fallback) ----
        st.markdown('<div class="section-header">📊 Valor por Processo</div>', unsafe_allow_html=True)

        proc_data = df_filtrado.groupby("Processo")["Valor"].sum().reset_index()
        proc_data = proc_data.sort_values("Valor", ascending=False)

        fig = px.bar(
            proc_data,
            x="Processo",
            y="Valor",
            color_discrete_sequence=["#6366f1"],
            text_auto='.2s',
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0", family="Inter"),
            xaxis=dict(title="Processo", tickangle=-45, gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(title="Valor (R$)", gridcolor="rgba(255,255,255,0.05)"),
            margin=dict(l=20, r=20, t=20, b=80),
            height=450,
        )
        fig.update_traces(
            marker_line_width=0,
            marker_cornerradius=6,
            textposition="outside",
            textfont_size=11,
        )
        st.plotly_chart(fig, use_container_width=True)


# ========================
# TABELA DETALHADA
# ========================
st.markdown('<div class="section-header">📋 Detalhamento dos Boletos em Aberto</div>', unsafe_allow_html=True)

if not df_filtrado.empty:
    colunas_exibir = [
        "Empresa", "Processo", "Cliente", "Número Título",
        "Número Documento", "Vencimento", "Valor", "Tags"
    ]
    colunas_disponiveis = [c for c in colunas_exibir if c in df_filtrado.columns]
    
    df_exibir = df_filtrado[colunas_disponiveis].copy()
    df_exibir = df_exibir.sort_values("Vencimento", ascending=True)
    
    # Formatar valor para exibição
    df_exibir["Valor"] = df_exibir["Valor"].apply(lambda v: formatar_brl(v))

    st.dataframe(
        df_exibir,
        use_container_width=True,
        height=450,
        hide_index=True,
    )
else:
    st.info("Nenhum boleto encontrado para os filtros selecionados.")


# ========================
# RODAPÉ
# ========================
st.markdown("""
<div style="text-align:center; padding:32px 0 16px 0; color:rgba(255,255,255,0.25); font-size:0.8rem;">
    Dashboard Financeiro — Dados via API Maino • Atualizado em tempo real
</div>
""", unsafe_allow_html=True)
