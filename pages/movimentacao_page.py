# pages/movimentacao_page.py
import streamlit as st
import pandas as pd
from supabase import Client
from utils import supabase_client_hash_func
import pytz # Biblioteca para lidar com fusos horários

# --- FUNÇÕES DE DADOS ---

@st.cache_data(ttl=30, hash_funcs={Client: supabase_client_hash_func})
def get_movimentacao_data(supabase_client: Client):
    """Busca a lista de produtos e o histórico de movimentações."""
    if not supabase_client:
        return [], pd.DataFrame()

    # Busca a lista de produtos para os formulários e filtros
    produtos_response = supabase_client.table('produtos').select('id, nome').order('nome').execute()
    lista_produtos = produtos_response.data
    
    # Busca o histórico completo de movimentações
    movimentacoes_response = supabase_client.table('movimentacoes').select(
        '*, produtos(nome)'
    ).order('data_movimentacao', desc=True).limit(2000).execute()
    
    df_movimentacoes = pd.DataFrame()
    if movimentacoes_response.data:
        df_movimentacoes = pd.json_normalize(movimentacoes_response.data)
        if 'produtos.nome' in df_movimentacoes.columns:
            df_movimentacoes = df_movimentacoes.rename(columns={'produtos.nome': 'produto_nome'})
        # Converte a coluna de data para o tipo datetime com fuso horário
        df_movimentacoes['data_movimentacao'] = pd.to_datetime(df_movimentacoes['data_movimentacao'])

    return lista_produtos, df_movimentacoes

def registrar_movimentacao(supabase_client: Client, id_produto: str, tipo: str, quantidade: int):
    """Registra a movimentação e atualiza o estoque via RPC."""
    response = supabase_client.rpc('atualizar_estoque', {
        'p_produto_id': id_produto, 
        'p_quantidade_movimentada': quantidade, 
        'p_tipo_mov': tipo
    }).execute()
    
    resultado = response.data
    if resultado == 'Sucesso':
        return True, "Movimentação registrada com sucesso!"
    else:
        return False, resultado

# --- PÁGINA PRINCIPAL ---

def render_page(supabase_client: Client):
    st.title("🚚 Controle e Rastreabilidade de Estoque")
    st.write("Registre entradas e saídas manuais e audite todo o histórico de movimentações do seu inventário.")

    lista_produtos, df_movimentacoes = get_movimentacao_data(supabase_client)
    produtos_dict = {produto['nome']: produto['id'] for produto in lista_produtos}

    # --- Formulário para registrar nova movimentação ---
    with st.expander("➕ Registrar Nova Movimentação (Entrada/Saída)"):
        if not produtos_dict:
            st.warning("Nenhum produto cadastrado. Adicione produtos na aba 'Produtos' primeiro.")
        else:
            produto_selecionado_nome = st.selectbox(
                "Selecione o Produto", 
                options=produtos_dict.keys(),
                key="mov_produto_select"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                tipo_movimentacao = st.radio("Tipo de Movimentação", ('ENTRADA', 'SAÍDA'), horizontal=True)
            with col2:
                quantidade = st.number_input("Quantidade", min_value=1, step=1)

            if st.button(f"Registrar {tipo_movimentacao}", use_container_width=True, type="primary"):
                id_produto_selecionado = produtos_dict[produto_selecionado_nome]
                with st.spinner("Processando..."):
                    sucesso, mensagem = registrar_movimentacao(
                        supabase_client, id_produto_selecionado, tipo_movimentacao, quantidade
                    )
                    if sucesso:
                        st.success(mensagem)
                        st.cache_data.clear() # Limpa o cache para atualizar o histórico
                        st.rerun()
                    else:
                        st.error(mensagem)
    
    st.divider()

    # --- Histórico de Movimentações ---
    st.subheader("📜 Histórico de Movimentações")

    if df_movimentacoes.empty:
        st.info("Nenhuma movimentação registrada ainda.")
        return

    # --- Filtros para o histórico ---
    # Converte a data UTC para o fuso de Brasília para os filtros
    brasilia_tz = pytz.timezone("America/Sao_Paulo")
    df_movimentacoes['data_local'] = df_movimentacoes['data_movimentacao'].dt.tz_convert(brasilia_tz)
    df_movimentacoes['data_filtro'] = df_movimentacoes['data_local'].dt.date

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        produtos_no_historico = sorted(df_movimentacoes['produto_nome'].unique())
        produto_filtrado = st.multiselect("Filtrar por Produto", options=produtos_no_historico)
    with col_f2:
        tipo_filtrado = st.selectbox("Filtrar por Tipo", options=["Todos", "ENTRADA", "SAÍDA"])
    with col_f3:
        min_date = df_movimentacoes['data_filtro'].min()
        max_date = df_movimentacoes['data_filtro'].max()
        periodo_filtrado = st.date_input(
            "Filtrar por Período",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

    # Aplicação dos filtros
    df_filtrado = df_movimentacoes.copy()
    if produto_filtrado:
        df_filtrado = df_filtrado[df_filtrado['produto_nome'].isin(produto_filtrado)]
    if tipo_filtrado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['tipo_movimentacao'] == tipo_filtrado]
    if len(periodo_filtrado) == 2:
        start_date, end_date = periodo_filtrado
        df_filtrado = df_filtrado[
            (df_filtrado['data_filtro'] >= start_date) & 
            (df_filtrado['data_filtro'] <= end_date)
        ]

    # Formatação para exibição
    df_display = df_filtrado.copy()
    df_display['data_formatada'] = df_display['data_local'].dt.strftime('%d/%m/%Y %H:%M:%S')

    st.dataframe(
        df_display.rename(columns={
            'data_formatada': 'Data e Hora (Brasília)',
            'produto_nome': 'Produto',
            'tipo_movimentacao': 'Tipo',
            'quantidade': 'Qtd.'
        })[['Data e Hora (Brasília)', 'Produto', 'Tipo', 'Qtd.']],
        use_container_width=True,
        hide_index=True
    )
