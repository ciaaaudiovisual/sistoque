import streamlit as st
from supabase import create_client
import pandas as pd

# --- Configuração e Conexão ---
st.set_page_config(page_title="Movimentar Estoque", layout="wide")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- Funções do Banco de Dados ---
def get_lista_produtos():
    response = supabase.table('produtos').select('id, nome').order('nome').execute()
    return response.data

def registrar_movimentacao(id_produto, tipo, quantidade):
    # Primeiro, busca o estoque atual
    produto_atual = supabase.table('produtos').select('estoque_atual').eq('id', id_produto).single().execute()
    estoque_atual = produto_atual.data['estoque_atual']

    # Calcula o novo estoque
    if tipo == 'ENTRADA':
        novo_estoque = estoque_atual + quantidade
    elif tipo == 'SAÍDA':
        if estoque_atual < quantidade:
            return False, "Estoque insuficiente para realizar a saída."
        novo_estoque = estoque_atual - quantidade
    
    # Atualiza o estoque na tabela de produtos
    supabase.table('produtos').update({'estoque_atual': novo_estoque}).eq('id', id_produto).execute()

    # Insere o registro na tabela de movimentações
    supabase.table('movimentacoes').insert({
        'id_produto': id_produto,
        'tipo_movimentacao': tipo,
        'quantidade': quantidade
    }).execute()
    
    return True, "Movimentação registrada com sucesso!"

# --- Layout da Página ---
st.title("🚚 Movimentação de Estoque")

lista_produtos = get_lista_produtos()
# Transforma a lista de dicionários em um dicionário para o selectbox
produtos_dict = {produto['nome']: produto['id'] for produto in lista_produtos}

if not produtos_dict:
    st.warning("Nenhum produto cadastrado. Adicione produtos na página de 'Gestão de Produtos' primeiro.")
else:
    produto_selecionado_nome = st.selectbox("Selecione a Bebida", options=produtos_dict.keys())
    id_produto_selecionado = produtos_dict[produto_selecionado_nome]

    col1, col2 = st.columns(2)
    with col1:
        tipo_movimentacao = st.radio("Tipo de Movimentação", ('ENTRADA', 'SAÍDA'), horizontal=True)
    with col2:
        quantidade = st.number_input("Quantidade", min_value=1, step=1)

    if st.button(f"Registrar {tipo_movimentacao}", use_container_width=True):
        sucesso, mensagem = registrar_movimentacao(id_produto_selecionado, tipo_movimentacao, quantidade)
        if sucesso:
            st.success(mensagem)
        else:
            st.error(mensagem)
