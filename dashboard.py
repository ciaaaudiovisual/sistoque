# 🏠_
import streamlit as st
from supabase import create_client, Client
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Dashboard de Estoque", layout="wide")

# Inicializa a conexão com o Supabase (só na primeira vez)
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- Funções de busca de dados ---
def get_total_produtos():
    response = supabase.table('produtos').select('id', count='exact').execute()
    return response.count

def get_produtos_baixo_estoque():
    # Traz produtos onde o estoque atual é menor ou igual ao mínimo
    response = supabase.rpc('get_produtos_baixo_estoque').execute()
    return pd.DataFrame(response.data)

# --- Layout do Dashboard ---
st.title("🍹 Dashboard de Controle de Bebidas")
st.markdown("Visão geral do seu negócio.")

# KPIs
col1, col2 = st.columns(2)
with col1:
    st.metric("Total de Produtos Cadastrados", get_total_produtos())

# Criar uma função no Supabase para otimizar a busca de baixo estoque
# Vá em SQL Editor > New Query e rode:
# CREATE OR REPLACE FUNCTION get_produtos_baixo_estoque()
# RETURNS TABLE(nome TEXT, estoque_atual INT, qtd_minima_estoque INT) AS $$
# BEGIN
#     RETURN QUERY
#     SELECT p.nome, p.estoque_atual, p.qtd_minima_estoque
#     FROM produtos p
#     WHERE p.estoque_atual <= p.qtd_minima_estoque;
# END;
# $$ LANGUAGE plpgsql;

with col2:
    df_baixo_estoque = get_produtos_baixo_estoque()
    st.metric("Produtos com Baixo Estoque", len(df_baixo_estoque))

st.subheader("⚠️ Alerta de Reposição")
if not df_baixo_estoque.empty:
    st.dataframe(df_baixo_estoque, use_container_width=True)
else:
    st.success("Tudo certo! Nenhum produto com estoque baixo.")

# Adicione mais gráficos e informações conforme necessário
