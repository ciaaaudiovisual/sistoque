import streamlit as st
from supabase import create_client
import pandas as pd



if 'user' not in st.session_state or st.session_state.user is None:
    st.error("🔒 Por favor, faça o login para acessar esta página.")
    st.page_link("dashboard.py", label="Ir para a página de Login", icon="🏠")
    st.stop() # Interrompe a execução
# --- Configuração e Conexão ---

if st.session_state.user_role != 'Admin':
    st.error("🚫 Acesso negado. Apenas Administradores podem visualizar os relatórios.")
    st.stop()
st.set_page_config(page_title="Relatórios", layout="wide")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

def get_relatorio_estoque():
    # Adicione 'preco_compra' à lista de colunas selecionadas
    response = supabase.table('produtos').select('nome, tipo, estoque_atual, qtd_minima_estoque, preco_venda, preco_compra').order('nome').execute()
    return pd.DataFrame(response.data)

def get_relatorio_movimentacoes():
    # Esta query pode ser otimizada com uma VIEW no Supabase para incluir o nome do produto
    response = supabase.table('movimentacoes').select('*, produtos(nome)').order('data_movimentacao', desc=True).execute()
    df = pd.json_normalize(response.data)
    # Renomear colunas para clareza
    if not df.empty:
        df = df.rename(columns={'produtos.nome': 'produto_nome'})
    return df


# --- Layout da Página ---
st.title("📊 Relatórios Gerenciais")

tab1, tab2, tab3 = st.tabs(["Estoque Atual", "Histórico de Movimentações", "Análise de Lucro (Simplificada)"])

with tab1:
    st.subheader("Relatório de Estoque Atual")
    df_estoque = get_relatorio_estoque()
    if not df_estoque.empty:
        st.dataframe(df_estoque, use_container_width=True)
    else:
        st.info("Nenhum dado de estoque para exibir.")

with tab2:
    st.subheader("Histórico de Movimentações")
    df_movimentacoes = get_relatorio_movimentacoes()
    if not df_movimentacoes.empty:
        st.dataframe(df_movimentacoes, use_container_width=True)
    else:
        st.info("Nenhuma movimentação registrada.")

with tab3:
    st.subheader("Análise de Lucro Potencial por Produto")
    df_lucro = get_relatorio_estoque()
    if not df_lucro.empty and 'preco_compra' in df_lucro.columns:
        df_lucro['lucro_por_unidade'] = df_lucro['preco_venda'] - df_lucro['preco_compra']
        df_lucro['lucro_potencial_total'] = df_lucro['lucro_por_unidade'] * df_lucro['estoque_atual']
        
        st.dataframe(df_lucro[['nome', 'lucro_por_unidade', 'estoque_atual', 'lucro_potencial_total']], use_container_width=True)
        
        st.bar_chart(df_lucro.set_index('nome')['lucro_potencial_total'])
    else:
        st.info("Dados insuficientes para calcular o lucro (verifique se os preços de compra e venda estão cadastrados).")
