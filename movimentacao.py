# pages/movimentacao.py
import streamlit as st
from supabase import create_client
import pandas as pd

# --- Verificação de Login ---
if 'user' not in st.session_state or st.session_state.user is None:
    st.error("🔒 Por favor, faça o login para acessar esta página.")
    st.page_link("dashboard.py", label="Ir para a página de Login", icon="🏠")
    st.stop()

# --- Configuração e Conexão ---
st.set_page_config(page_title="Movimentar Estoque", layout="wide")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- Funções do Banco de Dados ---
@st.cache_data
def get_lista_produtos():
    response = supabase.table('produtos').select('id, nome').order('nome').execute()
    return response.data

def registrar_movimentacao(id_produto, tipo, quantidade):
    # ATENÇÃO: Certifique-se de que a função 'atualizar_estoque' foi criada no SQL Editor do Supabase.
    response = supabase.rpc('atualizar_estoque', {
        'produto_id': id_produto,
        'quantidade_movimentada': quantidade,
        'tipo_mov': tipo
    }).execute()
    
    resultado = response.data
    if resultado == 'Sucesso':
        return True, "Movimentação registrada com sucesso!"
    else:
        # Retorna a mensagem de erro do banco de dados (ex: 'Estoque insuficiente')
        return False, resultado

# --- Layout da Página ---
st.title("🚚 Movimentação de Estoque")

lista_produtos = get_lista_produtos()
# Transforma a lista de dicionários em um dicionário para o selectbox
produtos_dict = {produto['nome']: produto['id'] for produto in lista_produtos}

if not produtos_dict:
    st.warning("Nenhum produto cadastrado. Adicione produtos na página de 'Gestão de Produtos' primeiro.")
else:
    produto_selecionado_nome = st.selectbox("Selecione a Bebida", options=produtos_dict.keys())
    
    if produto_selecionado_nome:
        id_produto_selecionado = produtos_dict[produto_selecionado_nome]

        col1, col2 = st.columns(2)
        with col1:
            tipo_movimentacao = st.radio("Tipo de Movimentação", ('ENTRADA', 'SAÍDA'), horizontal=True)
        with col2:
            quantidade = st.number_input("Quantidade", min_value=1, step=1)

        if st.button(f"Registrar {tipo_movimentacao}", use_container_width=True):
            with st.spinner("Processando..."):
                sucesso, mensagem = registrar_movimentacao(id_produto_selecionado, tipo_movimentacao, quantidade)
                if sucesso:
                    st.success(mensagem)
                    # Limpa o cache para que outros relatórios possam ver a mudança
                    st.cache_data.clear()
                else:
                    st.error(mensagem)
