# pages/1_📦_Gestão_de_Produtos.py
import streamlit as st
from supabase import create_client
import pandas as pd
import time

if 'user' not in st.session_state or st.session_state.user is None:
    st.error("🔒 Por favor, faça o login para acessar esta página.")
    st.page_link("dashboard.py", label="Ir para a página de Login", icon="🏠")
    st.stop() # Interrompe a execução

# Conexão (pode ser movida para um módulo separado depois)
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

st.title("Gestão de Produtos (Bebidas)")

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
                    # Upload da foto para o Supabase Storage
                    file_path = f"{nome.replace(' ', '_').lower()}_{int(time.time())}.{foto_produto.name.split('.')[-1]}"
                    supabase.storage.from_("fotos_produtos").upload(file_path, foto_produto.getvalue())
                    # Obter a URL pública
                    foto_url = supabase.storage.from_("fotos_produtos").get_public_url(file_path)

                # Inserir dados no banco
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
                else:
                    st.error(f"Erro ao cadastrar: {response.error.message}")

with tab2:
    st.subheader("Todos os Produtos")
    # Busca os dados
    response = supabase.table('produtos').select('*').order('nome').execute()
    df_produtos = pd.DataFrame(response.data)

    if not df_produtos.empty:
        # Usando st.data_editor para permitir edições
        df_editado = st.data_editor(
            df_produtos,
            column_config={
                "id": None, # Oculta a coluna ID
                "foto_url": st.column_config.ImageColumn("Foto", help="URL da imagem do produto"),
                "preco_compra": st.column_config.NumberColumn("Preço Compra", format="R$ %.2f"),
                "preco_venda": st.column_config.NumberColumn("Preço Venda", format="R$ %.2f"),
                "estoque_atual": st.column_config.NumberColumn("Estoque Atual"),
                "qtd_minima_estoque": st.column_config.NumberColumn("Estoque Mínimo"),
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic" # Permite deletar linhas
        )
        
        # Lógica para salvar as alterações (simplificada)
        if st.button("Salvar Alterações"):
            # Aqui você implementaria a lógica para comparar df_produtos com df_editado
            # e chamar supabase.table('produtos').update({...}).eq('id', ...).execute()
            # ou supabase.table('produtos').delete().eq('id', ...).execute()
            st.info("Funcionalidade de salvar em desenvolvimento!")

    else:
        st.info("Nenhum produto cadastrado ainda.")
