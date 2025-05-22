import streamlit as st
import pandas as pd
import requests
import re

# --- CONFIGURAÇÃO DO STREAMLIT ---
st.set_page_config(page_title="Dashboard de Boletos", layout="wide")

# --- ESTILO PERSONALIZADO (CSS) ---
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #f5f6fa;
    }

    h1, h2, h3, h4 {
        color: #00c7e6;
        font-family: 'Segoe UI', sans-serif;
    }

    div[data-testid="metric-container"] {
        background-color: #1e293b;
        padding: 20px;
        border-radius: 10px;
        color: #ffffff;
        border: 1px solid #00c7e6;
        margin: 5px 0;
    }

    button {
        background-color: #00c7e6 !important;
        color: black !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: bold !important;
    }

    div[data-testid="metric-container"] > label {
        color: #cbd5e1;
    }

    .stDataFrame {
        background-color: #1e1e2f;
        border-radius: 10px;
        padding: 10px;
    }

    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-thumb {
        background-color: #00c7e6;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Dashboard de Acompanhamento de Boletos")
st.markdown("---")

# Função segura para converter valores
def converter_valor(valor):
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
    except Exception as e:
        print(f"Erro ao converter valor: {valor} -> {e}")
        return 0.0

# Função para coletar dados paginados da API
def coletar_dados(access_token, nome_empresa):
    url_base = "https://api.maino.com.br/api/v2/contas_a_recebers"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    todos_os_dados = []
    pagina = 1

    while True:
        params = {"page": pagina, "per_page": 50}
        response = requests.get(url_base, headers=headers, params=params)

        if response.status_code != 200:
            st.error(f"Erro na coleta de {nome_empresa}: {response.status_code}")
            break

        dados = response.json()
        contas = dados.get("contas") or dados.get("data", {}).get("contas_a_receber", [])

        if not contas:
            break

        for conta in contas:
            valor = converter_valor(conta.get("valor", 0))
            todos_os_dados.append({
                "Número Título": conta.get("numero_titulo", ""),
                "Número Documento": conta.get("numero_fatura", ""),
                "Vencimento": conta.get("data_vencimento", ""),
                "Valor": valor,
                "Data Competência": conta.get("data_competencia", ""),
                "Data Pagamento": conta.get("data_pagamento", ""),
                "Cliente": conta.get("cliente", {}).get("razao_social", ""),
                "Processo": conta.get("processo", {}).get("codigo", "")
            })

        pagina += 1

    return pd.DataFrame(todos_os_dados)

# Lista de empresas (INSERIR SEUS DADOS AQUI)
empresas = []
empresas = st.secrets["empresas"]

# Botão para atualizar
if st.button("🔄 Atualizar Dados"):
    st.session_state["atualizar"] = True

# Executa coleta de dados no carregamento ou após clique
if "atualizar" not in st.session_state:
    st.session_state["atualizar"] = True

if st.session_state["atualizar"]:
    for empresa in empresas:
        nome = empresa["nome"]
        token = empresa["token"]

        st.header(f"🏢 {nome}")

        with st.spinner(f"Coletando dados da empresa {nome}..."):
            df = coletar_dados(token, nome)

        if df.empty:
            st.warning("Nenhum dado encontrado.")
            continue

        df_aberto = df[df["Data Pagamento"].isna()]
        if df_aberto.empty:
            st.info("Nenhum boleto em aberto encontrado.")
            continue

        total_valor = df_aberto['Valor'].sum()
        total_boletos = df_aberto.shape[0]

        col1, col2 = st.columns(2)
        with col1:
            st.metric("💰 Total a Receber (em aberto)", f"R$ {total_valor:,.2f}".replace('.', '#').replace(',', '.').replace('#', ','))
        with col2:
            st.metric("🧾 Total de Boletos em Aberto", total_boletos)

        st.markdown("### 📊 Valor a Receber por Processo (Boletos em Aberto)")
        valores_por_processo = df_aberto.groupby("Processo")["Valor"].sum().sort_values(ascending=False)
        st.bar_chart(valores_por_processo)

        st.markdown("### 📋 Dados Detalhados (Boletos em Aberto)")
        st.dataframe(df_aberto)

        st.markdown("---")

    # Limpa o estado para não recarregar sempre
    st.session_state["atualizar"] = False
