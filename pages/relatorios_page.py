import streamlit as st
import pandas as pd

@st.cache_data(ttl=60)
def get_relatorio_estoque(supabase_client):
    response = supabase_client.table('produtos').select('nome, tipo, estoque_atual, qtd_minima_estoque, preco_venda, preco_compra').order('nome').execute()
    return pd.DataFrame(response.data)

@st.cache_data(ttl=60)
def get_relatorio_movimentacoes(supabase_client):
    response = supabase_client.table('movimentacoes').select('*, produtos(nome)').order('data_movimentacao', desc=True).limit(1000).execute()
    df = pd.json_normalize(response.data)
    if not df.empty:
        df = df.rename(columns={'produtos.nome': 'produto_nome'})
    return df

def render_page(supabase_client):
    st.title("📊 Relatórios Gerenciais")

    if st.button("Recarregar Relatórios"):
        st.cache_data.clear()

    tab1, tab2, tab3 = st.tabs(["Estoque Atual", "Histórico de Movimentações", "Análise de Lucro"])

    with tab1:
        st.subheader("Relatório de Estoque Atual")
        df_estoque = get_relatorio_estoque(supabase_client)
        if not df_estoque.empty:
            st.dataframe(df_estoque, use_container_width=True)
        else:
            st.info("Nenhum dado de estoque para exibir.")

    with tab2:
        st.subheader("Histórico de Movimentações")
        df_movimentacoes = get_relatorio_movimentacoes(supabase_client)
        if not df_movimentacoes.empty:
            st.dataframe(df_movimentacoes, use_container_width=True)
        else:
            st.info("Nenhuma movimentação registrada.")

    with tab3:
        st.subheader("Análise de Lucro Potencial por Produto em Estoque")
        df_lucro = get_relatorio_estoque(supabase_client).copy()
        if not df_lucro.empty and 'preco_compra' in df_lucro.columns and 'preco_venda' in df_lucro.columns:
            df_lucro['lucro_por_unidade'] = df_lucro['preco_venda'] - df_lucro['preco_compra']
            df_lucro['lucro_potencial_total'] = df_lucro['lucro_por_unidade'] * df_lucro['estoque_atual']
            
            st.dataframe(df_lucro[['nome', 'lucro_por_unidade', 'estoque_atual', 'lucro_potencial_total']], use_container_width=True)
            
            st.bar_chart(df_lucro.set_index('nome')['lucro_potencial_total'])
        else:
            st.info("Dados insuficientes para calcular o lucro.")
