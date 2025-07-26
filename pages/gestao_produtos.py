import streamlit as st
import pandas as pd
import time

@st.cache_data(ttl=60)
def get_produtos(supabase_client):
    response = supabase_client.table('produtos').select('*').order('nome').execute()
    return pd.DataFrame(response.data)

def render_page(supabase_client):
    st.title("📦 Gestão de Produtos")

    if st.button("Recarregar Dados"):
        st.cache_data.clear()

    tab1, tab2 = st.tabs(["➕ Adicionar Novo Produto", "✏️ Visualizar e Editar"])

    with tab1:
        st.subheader("Cadastrar Novo Produto")
        with st.form("add_produto", clear_on_submit=True):
            nome = st.text_input("Nome do Produto", placeholder="Ex: X-Burger")
            tipo = st.text_input("Tipo/Categoria", placeholder="Ex: Lanche")
            preco_compra = st.number_input("Preço de Compra (R$)", min_value=0.0, format="%.2f")
            preco_venda = st.number_input("Preço de Venda (R$)", min_value=0.0, format="%.2f")
            qtd_minima = st.number_input("Estoque Mínimo", min_value=0, step=1)
            foto_produto = st.file_uploader("Foto do Produto", type=["png", "jpg", "jpeg"])
            submitted = st.form_submit_button("CADASTRAR")

            if submitted:
                # Lógica para adicionar produto...
                pass # A lógica completa já foi fornecida anteriormente

    with tab2:
        st.subheader("Todos os Produtos")
        df_produtos = get_produtos(supabase_client)
        if not df_produtos.empty:
            st.data_editor(df_produtos, key="editor_produtos", use_container_width=True) # A lógica de salvar foi fornecida anteriormente
        else:
            st.info("Nenhum produto cadastrado.")
