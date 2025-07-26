# pages/relatorios_page.py
import streamlit as st
import pandas as pd
from supabase import Client
from utils import supabase_client_hash_func

# CORREÇÃO: A função agora recebe o cliente supabase e usa o hash correto.
@st.cache_data(ttl=30, hash_funcs={Client: supabase_client_hash_func})
def get_relatorio_estoque(supabase_client: Client):
    """Busca dados de estoque atualizados."""
    if not supabase_client: return pd.DataFrame()
    response = supabase_client.table('produtos').select(
        'nome, tipo, estoque_atual, qtd_minima_estoque, preco_venda, preco_compra'
    ).order('nome').execute()
    return pd.DataFrame(response.data)

# CORREÇÃO: A função agora recebe o cliente supabase e usa o hash correto.
@st.cache_data(ttl=30, hash_funcs={Client: supabase_client_hash_func})
def get_relatorio_movimentacoes(supabase_client: Client):
    """Busca o histórico de movimentações atualizado."""
    if not supabase_client: return pd.DataFrame()
    response = supabase_client.table('movimentacoes').select(
        '*, produtos(nome)'
    ).order('data_movimentacao', desc=True).limit(1000).execute()
    
    if not response.data:
        return pd.DataFrame()
        
    df = pd.json_normalize(response.data)
    if 'produtos.nome' in df.columns:
        df = df.rename(columns={'produtos.nome': 'produto_nome'})
    return df

def render_page(supabase_client: Client):
    """Renderiza a página de relatórios gerenciais."""
    st.title("📊 Relatórios Gerenciais")

    if st.button("Recarregar Relatórios"):
        st.cache_data.clear()
        st.rerun()

    # CORREÇÃO: Os dados são buscados aqui, passando o cliente supabase.
    # O cache será invalidado pela ação no PDV ou pelo botão de recarregar.
    df_estoque = get_relatorio_estoque(supabase_client)
    df_movimentacoes = get_relatorio_movimentacoes(supabase_client)

    tab1, tab2, tab3 = st.tabs(["Estoque Atual", "Histórico de Movimentações", "Análise de Lucro"])

    with tab1:
        st.subheader("Relatório de Estoque Atual")
        if not df_estoque.empty:
            def highlight_low_stock(s):
                # Função para destacar produtos com estoque baixo ou igual ao mínimo.
                return ['background-color: #FFCDD2' if s.estoque_atual <= s.qtd_minima_estoque else '' for i in s.index]
            st.dataframe(df_estoque.style.apply(highlight_low_stock, axis=1), use_container_width=True)
        else:
            st.info("Nenhum dado de estoque para exibir.")

    with tab2:
        st.subheader("Histórico de Movimentações")
        if not df_movimentacoes.empty:
            st.dataframe(df_movimentacoes, use_container_width=True)
        else:
            st.info("Nenhuma movimentação registrada.")

    with tab3:
        st.subheader("Análise de Lucro Potencial por Produto em Estoque")
        if not df_estoque.empty and 'preco_compra' in df_estoque.columns and 'preco_venda' in df_estoque.columns:
            df_lucro = df_estoque.copy()
            df_lucro['lucro_por_unidade'] = df_lucro['preco_venda'] - df_lucro['preco_compra']
            df_lucro['lucro_potencial_total'] = df_lucro['lucro_por_unidade'] * df_lucro['estoque_atual']
            st.dataframe(df_lucro[['nome', 'estoque_atual', 'lucro_por_unidade', 'lucro_potencial_total']], use_container_width=True)
            st.bar_chart(df_lucro.set_index('nome')['lucro_potencial_total'])
        else:
            st.info("Dados insuficientes para calcular o lucro.")
