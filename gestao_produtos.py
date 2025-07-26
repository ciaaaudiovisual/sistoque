# pages/gestao_produtos.py
import streamlit as st
from supabase import create_client
import pandas as pd
import time

# --- Verificação de Login ---
if 'user' not in st.session_state or st.session_state.user is None:
    st.error("🔒 Por favor, faça o login para acessar esta página.")
    st.page_link("dashboard.py", label="Ir para a página de Login", icon="🏠")
    st.stop()

# --- Conexão ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

st.title("📦 Gestão de Produtos (Bebidas)")

# Botão para recarregar os dados do cache
if st.button("Recarregar Dados"):
    st.cache_data.clear()

# --- Funções ---
@st.cache_data
def get_produtos():
    response = supabase.table('produtos').select('*').order('nome').execute()
    return pd.DataFrame(response.data)

# --- Layout ---
tab1, tab2 = st.tabs(["➕ Adicionar Novo Produto", "✏️ Visualizar e Editar"])

with tab1:
    st.subheader("Cadastrar Nova Bebida")
    with st.form("add_produto", clear_on_submit=True):
        nome = st.text_input("Nome da Bebida", placeholder="Ex: Cerveja IPA")
        tipo = st.text_input("Tipo/Categoria", placeholder="Ex: Artesanal")
        preco_compra = st.number_input("Preço de Compra (R$)", min_value=0.0, format="%.2f")
        preco_venda = st.number_input("Preço de Venda (R$)", min_value=0.0, format="%.2f")
        qtd_minima = st.number_input("Estoque Mínimo", min_value=0, step=1)
        
        foto_produto = st.file_uploader("Foto do Produto", type=["png", "jpg", "jpeg"])

        submitted = st.form_submit_button("CADASTRAR")

        if submitted:
            if not nome:
                st.error("O nome do produto é obrigatório!")
            else:
                foto_url = None
                if foto_produto:
                    file_path = f"{nome.replace(' ', '_').lower()}_{int(time.time())}.{foto_produto.name.split('.')[-1]}"
                    supabase.storage.from_("fotos_produtos").upload(file_path, foto_produto.getvalue())
                    foto_url = supabase.storage.from_("fotos_produtos").get_public_url(file_path)

                novo_produto = {
                    "nome": nome,
                    "tipo": tipo,
                    "preco_compra": preco_compra,
                    "preco_venda": preco_venda,
                    "qtd_minima_estoque": qtd_minima,
                    "foto_url": foto_url
                }
                response = supabase.table("produtos").insert(novo_produto).execute()
                
                if response.data:
                    st.success("Produto cadastrado com sucesso!")
                    st.cache_data.clear() # Limpa o cache para a lista ser atualizada
                else:
                    st.error(f"Erro ao cadastrar: {response.error.message}")

with tab2:
    st.subheader("Todos os Produtos")
    df_produtos = get_produtos()

    if not df_produtos.empty:
        df_editado = st.data_editor(
            df_produtos,
            column_config={
                "id": None,
                "foto_url": st.column_config.ImageColumn("Foto", help="URL da imagem do produto"),
                "preco_compra": st.column_config.NumberColumn("Preço Compra", format="R$ %.2f"),
                "preco_venda": st.column_config.NumberColumn("Preço Venda", format="R$ %.2f"),
                "estoque_atual": st.column_config.NumberColumn("Estoque Atual"),
                "qtd_minima_estoque": st.column_config.NumberColumn("Estoque Mínimo"),
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic"
        )
        
        if st.button("Salvar Alterações"):
            with st.spinner("Salvando..."):
                # Converte os dataframes para dicionários para facilitar a comparação
                originais = df_produtos.set_index('id').to_dict('index')
                editados = df_editado.set_index('id').to_dict('index')

                # Itera sobre os produtos editados para encontrar modificações
                for prod_id, prod_data in editados.items():
                    if prod_id in originais and prod_data != originais[prod_id]:
                        supabase.table('produtos').update(prod_data).eq('id', prod_id).execute()

                # Verifica se algum produto foi deletado
                ids_deletados = set(originais.keys()) - set(editados.keys())
                if ids_deletados:
                    for prod_id in ids_deletados:
                        supabase.table('produtos').delete().eq('id', prod_id).execute()
                
                st.success("Alterações salvas com sucesso!")
                st.cache_data.clear()
                st.rerun()
    else:
        st.info("Nenhum produto cadastrado ainda.")
