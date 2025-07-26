# pages/relatorios_page.py

import streamlit as st
import pandas as pd
from utils import init_connection # Importa a função de conexão

# --- FUNÇÕES CORRIGIDAS ---

@st.cache_data(ttl=60)
def get_relatorio_estoque():
    """Busca dados do estoque. A conexão é obtida aqui dentro."""
    supabase = init_connection()
    response = supabase.table('produtos').select('nome, tipo, estoque_atual, qtd_minima_estoque, preco_venda, preco_compra').order('nome').execute()
    return pd.DataFrame(response.data)

@st.cache_data(ttl=60)
def get_relatorio_movimentacoes():
    """Busca o histórico de movimentações. A conexão é obtida aqui dentro."""
    supabase = init_connection()
    response = supabase.table('movimentacoes').select('*, produtos(nome)').order('data_movimentacao', desc=True).limit(1000).execute()
    df = pd.json_normalize(response.data)
    if not df.empty:
        df = df.rename(columns={'produtos.nome': 'produto_nome'})
    return df

# --- FUNÇÃO PRINCIPAL DA PÁGINA ---

def render_page(supabase_client):
    """Renderiza a página de relatórios gerenciais."""
    st.title("📊 Relatórios Gerenciais")

    if st.button("Recarregar Relatórios"):
        st.cache_data.clear()

    tab1, tab2, tab3 = st.tabs(["Estoque Atual", "Histórico de Movimentações", "Análise de Lucro"])

    with tab1:
        st.subheader("Relatório de Estoque Atual")
        
        # --- CHAMADA DA FUNÇÃO CORRIGIDA ---
        df_estoque = get_relatorio_estoque() 

        if not df_estoque.empty:
            st.dataframe(df_estoque, use_container_width=True)
        else:
            st.info("Nenhum dado de estoque para exibir.")

    with tab2:
        st.subheader("Histórico de Movimentações")

        # --- CHAMADA DA FUNÇÃO CORRIGIDA ---
        df_movimentacoes = get_relatorio_movimentacoes()

        if not df_movimentacoes.empty:
            st.dataframe(df_movimentacoes, use_container_width=True)
        else:
            st.info("Nenhuma movimentação registrada.")

    with tab3:
        st.subheader("Análise de Lucro Potencial por Produto em Estoque")
        
        # --- CHAMADA DA FUNÇÃO CORRIGIDA ---
        df_lucro = get_relatorio_estoque().copy()

        if not df_lucro.empty and 'preco_compra' in df_lucro.columns and 'preco_venda' in df_lucro.columns:
            df_lucro['lucro_por_unidade'] = df_lucro['preco_venda'] - df_lucro['preco_compra']
            df_lucro['lucro_potencial_total'] = df_lucro['lucro_por_unidade'] * df_lucro['estoque_atual']
            
            st.dataframe(df_lucro[['nome', 'lucro_por_unidade', 'estoque_atual', 'lucro_potencial_total']], use_container_width=True)
            
            st.bar_chart(df_lucro.set_index('nome')['lucro_potencial_total'])
        else:
            st.info("Dados insuficientes para calcular o lucro.")
