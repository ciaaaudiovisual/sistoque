# pages/relatorios_page.py
import streamlit as st
import pandas as pd
from supabase import Client
from utils import supabase_client_hash_func
from datetime import datetime

@st.cache_data(ttl=30, hash_funcs={Client: supabase_client_hash_func})
def get_relatorios_data(supabase_client: Client):
    """Busca todos os dados necessários para os relatórios de uma só vez."""
    if not supabase_client:
        return pd.DataFrame(), pd.DataFrame()

    produtos_response = supabase_client.table('produtos').select(
        'nome, tipo, estoque_atual, qtd_minima_estoque, preco_venda, preco_compra'
    ).order('nome').execute()
    
    movimentacoes_response = supabase_client.table('movimentacoes').select(
        '*, produtos(nome)'
    ).order('data_movimentacao', desc=True).limit(2000).execute()

    df_estoque = pd.DataFrame(produtos_response.data)
    
    df_movimentacoes = pd.DataFrame()
    if movimentacoes_response.data:
        df_movimentacoes = pd.json_normalize(movimentacoes_response.data)
        if 'produtos.nome' in df_movimentacoes.columns:
            df_movimentacoes = df_movimentacoes.rename(columns={'produtos.nome': 'produto_nome'})
        # Converte a coluna de data para o tipo datetime com fuso horário (timezone-aware)
        df_movimentacoes['data_movimentacao'] = pd.to_datetime(df_movimentacoes['data_movimentacao'])

    return df_estoque, df_movimentacoes

def render_page(supabase_client: Client):
    st.title("📊 Painel de Relatórios Gerenciais")
    st.write("Analise o desempenho e a saúde do seu negócio em tempo real.")

    if st.button("Recarregar Dados"):
        st.cache_data.clear()
        st.rerun()

    df_estoque, df_movimentacoes = get_relatorios_data(supabase_client)

    if df_estoque.empty:
        st.warning("Não há dados de produtos para exibir. Cadastre produtos primeiro.")
        return

    tab1, tab2, tab3 = st.tabs(["📈 Resumo do Estoque", "📜 Histórico de Movimentações", "💰 Análise de Lucro"])

    with tab1:
        st.subheader("Visão Geral do Estoque")
        
        total_itens = df_estoque['estoque_atual'].sum()
        valor_estoque_venda = (df_estoque['estoque_atual'] * df_estoque['preco_venda']).sum()
        produtos_baixo_estoque = df_estoque[df_estoque['estoque_atual'] <= df_estoque['qtd_minima_estoque']].shape[0]

        col1, col2, col3 = st.columns(3)
        col1.metric("Itens Totais em Estoque", f"{total_itens:,.0f}")
        col2.metric("Valor de Venda do Estoque", f"R$ {valor_estoque_venda:,.2f}")
        col3.metric("Produtos com Estoque Baixo", produtos_baixo_estoque)
        
        st.divider()

        st.subheader("Detalhes dos Produtos")
        st.info("Esta é a sua 'tabela de estoque'. A coluna `estoque_atual` é atualizada automaticamente a cada entrada ou saída.", icon="ℹ️")
        
        df_display_estoque = df_estoque.rename(columns={
            'nome': 'Produto', 'tipo': 'Categoria', 'estoque_atual': 'Estoque',
            'qtd_minima_estoque': 'Estoque Mínimo', 'preco_venda': 'Preço Venda (R$)',
            'preco_compra': 'Preço Compra (R$)'
        })
        st.dataframe(df_display_estoque, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Filtrar Histórico de Movimentações")

        if df_movimentacoes.empty:
            st.info("Nenhuma movimentação registrada ainda.")
        else:
            col_filter1, col_filter2 = st.columns(2)
            with col_filter1:
                produtos_disponiveis = sorted(df_movimentacoes['produto_nome'].unique())
                produto_selecionado = st.multiselect("Filtrar por Produto", options=produtos_disponiveis)
            with col_filter2:
                min_date = df_movimentacoes['data_movimentacao'].min().date()
                max_date = df_movimentacoes['data_movimentacao'].max().date()
                data_selecionada = st.date_input(
                    "Filtrar por Período",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )

            df_filtrado = df_movimentacoes.copy()
            if produto_selecionado:
                df_filtrado = df_filtrado[df_filtrado['produto_nome'].isin(produto_selecionado)]
            
            # --- CORREÇÃO APLICADA AQUI ---
            # Garante que a comparação de datas seja feita com fusos horários compatíveis.
            if len(data_selecionada) == 2:
                try:
                    # Converte as datas do filtro para o mesmo fuso horário (UTC) dos dados do banco.
                    start_date = pd.to_datetime(data_selecionada[0]).tz_localize('UTC')
                    end_date = pd.to_datetime(data_selecionada[1]).replace(hour=23, minute=59, second=59).tz_localize('UTC')
                    
                    df_filtrado = df_filtrado[
                        (df_filtrado['data_movimentacao'] >= start_date) & 
                        (df_filtrado['data_movimentacao'] <= end_date)
                    ]
                except Exception as e:
                    st.error(f"Ocorreu um erro ao filtrar as datas: {e}")

            st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("Análise de Lucro Potencial")
        
        df_lucro = df_estoque.copy()
        df_lucro['lucro_unidade'] = df_lucro['preco_venda'] - df_lucro['preco_compra']
        df_lucro['lucro_potencial_total'] = df_lucro['lucro_unidade'] * df_lucro['estoque_atual']
        
        lucro_total_potencial = df_lucro['lucro_potencial_total'].sum()
        st.metric("Lucro Potencial Total em Estoque", f"R$ {lucro_total_potencial:,.2f}")
        
        st.dataframe(
            df_lucro[['nome', 'estoque_atual', 'lucro_unidade', 'lucro_potencial_total']].rename(columns={
                'nome': 'Produto', 'estoque_atual': 'Estoque', 'lucro_unidade': 'Lucro/Unidade (R$)',
                'lucro_potencial_total': 'Lucro Potencial Total (R$)'
            }),
            use_container_width=True, hide_index=True
        )

        st.bar_chart(df_lucro.set_index('nome')['lucro_potencial_total'])
