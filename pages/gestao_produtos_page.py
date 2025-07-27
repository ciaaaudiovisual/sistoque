# pages/gestao_produtos_page.py
import streamlit as st
import pandas as pd
import time
from supabase import Client
from utils import supabase_client_hash_func
import io
import requests

# --- FUNÇÕES DE DADOS (CACHE) ---
@st.cache_data(ttl=60, hash_funcs={Client: supabase_client_hash_func})
def get_produtos(supabase_client: Client):
    """Busca todos os produtos do banco de dados."""
    try:
        response = supabase_client.table('produtos').select('*').order('nome').execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Erro ao buscar produtos: {e}")
        return pd.DataFrame()

def buscar_foto_online(nome_produto):
    """Busca uma foto no Unsplash."""
    try:
        api_key = st.secrets.get("UNSPLASH_ACCESS_KEY")
        if not api_key: return None
        headers = {"Authorization": f"Client-ID {api_key}"}
        params = {"query": nome_produto, "per_page": 1, "orientation": "landscape"}
        response = requests.get("https://api.unsplash.com/search/photos", headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if data['results']:
            return data['results'][0]['urls']['regular']
    except Exception:
        return None
    return None

# --- FUNÇÃO PRINCIPAL DA PÁGINA ---
def render_page(supabase_client: Client):
    st.title("📦 Gestão de Produtos")

    # --- INICIALIZAÇÃO DO ESTADO DA SESSÃO PARA EDIÇÃO ---
    # Usamos isso para saber qual produto está sendo editado.
    if 'editing_product_id' not in st.session_state:
        st.session_state.editing_product_id = None

    if st.button("Recarregar Dados", key="reload_produtos"):
        st.cache_data.clear()
        st.session_state.editing_product_id = None
        st.rerun()

    tab_add, tab_view, tab_bulk = st.tabs([
        "➕ Adicionar Novo Produto",
        "✏️ Visualizar e Editar",
        "🚀 Importar / Atualizar em Massa"
    ])

    # --- ABA DE ADICIONAR PRODUTO ---
    with tab_add:
        with st.form("add_produto", clear_on_submit=True):
            st.subheader("Cadastrar Novo Produto")
            nome = st.text_input("Nome do Produto*", placeholder="Ex: X-Burger")
            tipo = st.text_input("Tipo/Categoria", placeholder="Ex: Lanche")
            
            st.markdown("---")
            buscar_online = st.checkbox("Buscar foto online automaticamente", value=True)
            foto_produto = None
            if not buscar_online:
                foto_produto = st.file_uploader("Ou envie uma foto manualmente", type=["png", "jpg", "jpeg"])
            st.markdown("---")
            
            codigo_barras = st.text_input("Código de Barras", placeholder="Ex: 7891234567890")
            col_preco1, col_preco2 = st.columns(2)
            preco_compra = col_preco1.number_input("Preço de Compra (R$)", min_value=0.0, format="%.2f")
            preco_venda = col_preco2.number_input("Preço de Venda (R$)", min_value=0.0, format="%.2f")
            qtd_minima = st.number_input("Estoque Mínimo", min_value=0, step=1)
            
            if st.form_submit_button("CADASTRAR PRODUTO", type="primary", use_container_width=True):
                if not nome:
                    st.error("O nome do produto é obrigatório!")
                else:
                    with st.spinner("Cadastrando..."):
                        foto_url = None
                        if buscar_online:
                            foto_url = buscar_foto_online(nome)
                        elif foto_produto:
                            try:
                                file_path = f"{nome.replace(' ', '_').lower()}_{int(time.time())}.{foto_produto.name.split('.')[-1]}"
                                supabase_client.storage.from_("fotos_produtos").upload(file_path, foto_produto.getvalue())
                                foto_url = supabase_client.storage.from_("fotos_produtos").get_public_url(file_path)
                            except Exception as e:
                                st.error(f"Falha no upload: {e}")
                        
                        novo_produto = {
                            "nome": nome, "tipo": tipo, "preco_compra": preco_compra,
                            "preco_venda": preco_venda, "qtd_minima_estoque": qtd_minima,
                            "foto_url": foto_url, "codigo_barras": codigo_barras or None,
                            "estoque_atual": 0, "status": 'Ativo'
                        }
                        
                        try:
                            supabase_client.table("produtos").insert(novo_produto).execute()
                            st.success("Produto cadastrado com sucesso!")
                            st.cache_data.clear()
                        except Exception as e:
                            st.error(f"Erro ao cadastrar no banco de dados: {e}")

    # --- ABA DE VISUALIZAR E EDITAR (REFORMULADA) ---
    with tab_view:
        st.subheader("Catálogo de Produtos")
        df_produtos = get_produtos(supabase_client)
        
        if df_produtos.empty:
            st.info("Nenhum produto cadastrado ainda.")
        else:
            search_term = st.text_input("🔎 Buscar produto por nome", placeholder="Digite para filtrar...")
            if search_term:
                df_produtos = df_produtos[df_produtos['nome'].str.contains(search_term, case=False, na=False)]

            # Função para definir o ID do produto a ser editado
            def set_editing_product(product_id):
                st.session_state.editing_product_id = product_id

            # Exibe os produtos em cards
            for index, produto in df_produtos.iterrows():
                cor_status = '#28a745' if produto.get('status') == 'Ativo' else '#dc3545'
                with st.container(border=True):
                    col1, col2, col3 = st.columns([1, 4, 1.2])
                    with col1:
                        st.image(produto.get('foto_url') or 'https://placehold.co/300x300/f0f2f6/777?text=Sem+Foto', width=100)
                    with col2:
                        st.markdown(f"**{produto['nome']}**")
                        st.caption(f"Categoria: {produto.get('tipo', 'N/A')}")
                        st.markdown(f"<span style='background-color: {cor_status}; color: white; padding: 3px 8px; border-radius: 15px; font-size: 12px;'>{produto.get('status')}</span>", unsafe_allow_html=True)
                    with col3:
                        st.metric("Estoque", f"{produto.get('estoque_atual', 0)}")
                        # Botão que define o ID no session_state e dispara o rerun
                        st.button("✏️ Editar", key=f"edit_{produto['id']}", on_click=set_editing_product, args=(produto['id'],), use_container_width=True)

    # --- LÓGICA DO POP-UP DE EDIÇÃO (FORA DO LOOP) ---
    if st.session_state.editing_product_id:
        # Encontra os dados do produto selecionado
        produto_para_editar = df_produtos[df_produtos['id'] == st.session_state.editing_product_id].iloc[0].to_dict()

        with st.dialog(f"Editando: {produto_para_editar['nome']}"):
            with st.form(key=f"form_edit_{produto_para_editar['id']}"):
                
                novo_nome = st.text_input("Nome", value=produto_para_editar.get('nome', ''))
                novo_tipo = st.text_input("Categoria", value=produto_para_editar.get('tipo', ''))
                
                col_edit1, col_edit2 = st.columns(2)
                novo_preco_venda = col_edit1.number_input("Preço Venda", value=float(produto_para_editar.get('preco_venda', 0)), format="%.2f")
                novo_preco_compra = col_edit2.number_input("Preço Compra", value=float(produto_para_editar.get('preco_compra', 0)), format="%.2f")
                
                novo_status = st.selectbox("Status", options=['Ativo', 'Inativo'], index=['Ativo', 'Inativo'].index(produto_para_editar.get('status', 'Ativo')))
                nova_foto = st.file_uploader("Trocar Foto", type=['png', 'jpg', 'jpeg'])

                btn_col1, btn_col2 = st.columns(2)
                if btn_col1.form_submit_button("✅ Salvar", use_container_width=True, type="primary"):
                    with st.spinner("Salvando..."):
                        update_data = {
                            'nome': novo_nome, 'tipo': novo_tipo,
                            'preco_venda': novo_preco_venda, 'preco_compra': novo_preco_compra,
                            'status': novo_status
                        }
                        if nova_foto:
                            try:
                                file_path = f"edit_{novo_nome.replace(' ', '_').lower()}_{int(time.time())}.{nova_foto.name.split('.')[-1]}"
                                supabase_client.storage.from_("fotos_produtos").upload(file_path, nova_foto.getvalue(), file_options={"cache-control": "3600", "upsert": "true"})
                                update_data['foto_url'] = supabase_client.storage.from_("fotos_produtos").get_public_url(file_path)
                            except Exception as e:
                                st.error(f"Erro no upload: {e}")

                        try:
                            supabase_client.table('produtos').update(update_data).eq('id', st.session_state.editing_product_id).execute()
                            st.success("Produto atualizado!")
                            st.session_state.editing_product_id = None
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                
                if btn_col2.form_submit_button("Cancelar", use_container_width=True):
                    st.session_state.editing_product_id = None
                    st.rerun()

    # --- ABA DE IMPORTAÇÃO EM MASSA ---
    with tab_bulk:
        st.subheader("Importar / Atualizar em Massa")
        # ... (código da importação em massa mantido como original)

    with tab_bulk:
        st.subheader("Importação e Atualização em Massa via CSV")
        st.markdown("""
        Use esta seção para adicionar novos produtos ou atualizar produtos existentes em lote.
        
        1.  **Baixe o modelo CSV** para ver o formato correto.
        2.  **Preencha o modelo** com seus dados. Para **atualizar** um produto, mantenha o `id` dele. Para **adicionar** um novo produto, deixe o campo `id` em branco.
        3.  **Envie o arquivo** preenchido.
        """)

        modelo_data = {
            'id': [1, None],
            'nome': ['Produto Exemplo A (para atualizar)', 'Produto Exemplo B (novo)'],
            'tipo': ['Categoria Exemplo', 'Nova Categoria'],
            'codigo_barras': ['111222333', '444555666'],
            'preco_compra': [10.50, 25.00],
            'preco_venda': [15.75, 40.00],
            'qtd_minima_estoque': [10, 5],
            'estoque_atual': [100, 50]
        }
        modelo_df = pd.DataFrame(modelo_data)
        
        csv_buffer = io.StringIO()
        modelo_df.to_csv(csv_buffer, index=False, sep=';')
        csv_bytes = csv_buffer.getvalue().encode('utf-8')
        
        st.download_button(
            label="📥 Baixar Modelo CSV",
            data=csv_bytes,
            file_name='modelo_produtos.csv',
            mime='text/csv',
        )

        uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv")
        if uploaded_file is not None:
            try:
                df_upload = pd.read_csv(uploaded_file, sep=';')
                st.write("Pré-visualização dos dados a serem importados/atualizados:")
                st.dataframe(df_upload)

                if st.button("CONFIRMAR E PROCESSAR ARQUIVO", type="primary"):
                    with st.spinner("Processando dados... Isso pode levar alguns minutos."):
                        registros = df_upload.to_dict(orient='records')
                        
                        response = supabase_client.table('produtos').upsert(registros, on_conflict='id').execute()

                        if response.data:
                            num_registros = len(response.data)
                            st.success(f"Operação concluída com sucesso! {num_registros} registros foram processados.")
                            st.cache_data.clear()
                        else:
                             st.error(f"Erro ao processar o arquivo: {response.error.message if response.error else 'Erro desconhecido'}")
            
            except Exception as e:
                st.error(f"Erro ao ler o arquivo CSV. Verifique o formato e o separador (deve ser ponto e vírgula ';'). Detalhes: {e}")
