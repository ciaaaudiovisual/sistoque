# pages/gestao_produtos_page.py
import streamlit as st
import pandas as pd
import time
from supabase import Client
from utils import supabase_client_hash_func
import io

@st.cache_data(ttl=60, hash_funcs={Client: supabase_client_hash_func})
def get_produtos(supabase_client: Client):
    response = supabase_client.table('produtos').select('*').order('id').execute()
    return pd.DataFrame(response.data)

@st.cache_data(ttl=60, hash_funcs={Client: supabase_client_hash_func})
def get_fornecedores(supabase_client: Client):
    response = supabase_client.table('fornecedores').select('id, nome').order('nome').execute()
    return {fornecedor['nome']: fornecedor['id'] for fornecedor in response.data}


def render_page(supabase_client: Client):
    """Renderiza a página de gestão de produtos."""
    st.title("📦 Gestão de Produtos")

    if st.button("Recarregar Dados", key="reload_produtos"):
        st.cache_data.clear()
        st.rerun()

    tab_add, tab_view, tab_bulk = st.tabs([
        "➕ Adicionar Novo Produto",
        "✏️ Visualizar e Editar",
        "🚀 Importar / Atualizar em Massa"
    ])

    with tab_add:
        st.subheader("Cadastrar Novo Produto")
        with st.form("add_produto", clear_on_submit=True):
            nome = st.text_input("Nome do Produto", placeholder="Ex: X-Burger")
            tipo = st.text_input("Tipo/Categoria", placeholder="Ex: Lanche")
            codigo_barras = st.text_input("Código de Barras (Opcional)", placeholder="Ex: 7891234567890")
            preco_compra = st.number_input("Preço de Compra (R$)", min_value=0.0, format="%.2f")
            preco_venda = st.number_input("Preço de Venda (R$)", min_value=0.0, format="%.2f")
            qtd_minima = st.number_input("Estoque Mínimo", min_value=0, step=1)
            foto_produto = st.file_uploader("Foto do Produto", type=["png", "jpg", "jpeg"])
            
            submitted = st.form_submit_button("CADASTRAR PRODUTO")

            if submitted:
                if not nome:
                    st.error("O nome do produto é obrigatório!")
                else:
                    foto_url = None
                    if foto_produto:
                        try:
                            file_path = f"{nome.replace(' ', '_').lower()}_{int(time.time())}.{foto_produto.name.split('.')[-1]}"
                            supabase_client.storage.from_("fotos_produtos").upload(file_path, foto_produto.getvalue())
                            foto_url = supabase_client.storage.from_("fotos_produtos").get_public_url(file_path)
                        except Exception as e:
                            st.warning(f"Não foi possível fazer o upload da foto: {e}")

                    novo_produto = {
                        "nome": nome, "tipo": tipo, "preco_compra": preco_compra,
                        "preco_venda": preco_venda, "qtd_minima_estoque": qtd_minima,
                        "foto_url": foto_url,
                        # Inclui o código de barras somente se preenchido
                        "codigo_barras": codigo_barras if codigo_barras else None
                    }
                    # O ID não é enviado, o banco de dados o gera automaticamente.
                    response = supabase_client.table("produtos").insert(novo_produto).execute()
                    
                    if response.data:
                        st.success("Produto cadastrado com sucesso!")
                        st.cache_data.clear()
                    else:
                        st.error(f"Erro ao cadastrar: {response.error.message if response.error else 'Erro desconhecido'}")
    
    with tab_view:
        st.subheader("Catálogo de Produtos")
    
        # --- 1. CAMPO DE BUSCA INTERATIVO ---
        df_produtos = get_produtos(supabase_client)
        
        if df_produtos.empty:
            st.info("Nenhum produto cadastrado ainda.")
        else:
            search_term = st.text_input("🔎 Buscar produto por nome", placeholder="Digite o nome do produto...")
            if search_term:
                df_produtos = df_produtos[df_produtos['nome'].str.contains(search_term, case=False, na=False)]
    
            # --- 2. GALERIA DE PRODUTOS EM FORMATO DE CARDS ---
            for index, produto in df_produtos.iterrows():
                # Define a cor do status para o badge visual
                status_info = {
                    'Ativo': ('#28a745', 'Ativo'),
                    'Inativo': ('#dc3545', 'Inativo')
                }
                cor_status, texto_status = status_info.get(produto.get('status', 'Inativo'), ('#6c757d', 'Desconhecido'))
    
                with st.container(border=True):
                    col1, col2, col3 = st.columns([1, 4, 1])
    
                    with col1:
                        st.image(produto.get('foto_url', 'https://placehold.co/300x300/f0f2f6/777?text=Sem+Foto'), width=100)
    
                    with col2:
                        st.markdown(f"**{produto['nome']}**")
                        st.caption(f"Categoria: {produto.get('tipo', 'N/A')}")
                        # Badge de Status
                        st.markdown(f"<span style='background-color: {cor_status}; color: white; padding: 3px 8px; border-radius: 15px; font-size: 12px;'>{texto_status}</span>", unsafe_allow_html=True)
    
                    with col3:
                        # --- 3. BOTÃO QUE ABRE O POP-UP DE EDIÇÃO ---
                        if st.button("✏️ Editar", key=f"edit_{produto['id']}", use_container_width=True):
                            # O st.dialog cria o pop-up
                            with st.dialog(f"Editando: {produto['nome']}", ):
                                with st.form(key=f"form_edit_{produto['id']}"):
                                    st.subheader("Informações do Produto")
                                    
                                    # Campos do formulário preenchidos com os dados atuais
                                    novo_nome = st.text_input("Nome do Produto", value=produto['nome'])
                                    novo_tipo = st.text_input("Tipo/Categoria", value=produto.get('tipo', ''))
                                    novo_codigo_barras = st.text_input("Código de Barras", value=produto.get('codigo_barras', ''))
                                    
                                    # Validade (com tratamento para data nula)
                                    data_validade_atual = pd.to_datetime(produto.get('data_validade')).date() if pd.notna(produto.get('data_validade')) else None
                                    nova_data_validade = st.date_input("Data de Validade", value=data_validade_atual)
                                    
                                    st.subheader("Valores e Status")
                                    col_form1, col_form2 = st.columns(2)
                                    with col_form1:
                                        novo_preco_venda = st.number_input("Preço de Venda (R$)", value=float(produto['preco_venda']), format="%.2f")
                                        novo_preco_compra = st.number_input("Preço de Compra (R$)", value=float(produto['preco_compra']), format="%.2f")
                                    with col_form2:
                                        novo_status = st.selectbox("Status", options=['Ativo', 'Inativo'], index=['Ativo', 'Inativo'].index(produto.get('status', 'Ativo')))
                                        st.metric("Estoque Atual", produto['estoque_atual'])
                                    
                                    st.subheader("Foto")
                                    nova_foto = st.file_uploader("Trocar Foto do Produto", type=['png', 'jpg', 'jpeg'])
    
                                    if st.form_submit_button("✅ Salvar Alterações", use_container_width=True, type="primary"):
                                        with st.spinner("Salvando..."):
                                            update_data = {
                                                'nome': novo_nome,
                                                'tipo': novo_tipo,
                                                'codigo_barras': novo_codigo_barras,
                                                'data_validade': str(nova_data_validade) if nova_data_validade else None,
                                                'preco_venda': novo_preco_venda,
                                                'preco_compra': novo_preco_compra,
                                                'status': novo_status
                                            }
    
                                            # Lógica para atualizar a foto apenas se uma nova foi enviada
                                            if nova_foto:
                                                try:
                                                    file_path = f"{novo_nome.replace(' ', '_').lower()}_{int(time.time())}.{nova_foto.name.split('.')[-1]}"
                                                    supabase_client.storage.from_("fotos_produtos").upload(file_path, nova_foto.getvalue(), file_options={"cache-control": "3600", "upsert": "true"})
                                                    foto_url = supabase_client.storage.from_("fotos_produtos").get_public_url(file_path)
                                                    update_data['foto_url'] = foto_url
                                                except Exception as e:
                                                    st.error(f"Erro no upload da nova foto: {e}")
                                            
                                            # Executa a atualização no banco de dados
                                            response = supabase_client.table('produtos').update(update_data).eq('id', produto['id']).execute()
    
                                            if not response.data:
                                                st.error(f"Erro ao atualizar: {response.error.message if response.error else 'Verifique as permissões'}")
                                            else:
                                                st.success("Produto atualizado com sucesso!")
                                                st.cache_data.clear() # Limpa o cache para recarregar os dados
                                                st.rerun() # Recarrega a página para mostrar as alterações
    
    with tab_bulk:
        st.subheader("Importação e Atualização em Massa via CSV")
        st.markdown("""
        Use esta seção para adicionar novos produtos ou atualizar produtos existentes em lote.
        
        1.  **Baixe o modelo CSV** para ver o formato correto.
        2.  **Preencha o modelo** com seus dados. Para **atualizar** um produto, mantenha o `id` dele. Para **adicionar** um novo produto, deixe o campo `id` em branco.
        3.  **Envie o arquivo** preenchido.
        """)

        # Gerar e fornecer o modelo CSV para download
        modelo_data = {
            'id': [1, None],
            'nome': ['Produto Exemplo A (para atualizar)', 'Produto Exemplo B (novo)'],
            'tipo': ['Categoria Exemplo', 'Nova Categoria'],
            'codigo_barras': ['111222333', '444555666'],
            'preco_compra': [10.50, 25.00],
            'preco_venda': [15.75, 40.00],
            'qtd_minima_estoque': [10, 5],
            'estoque_atual': [100, 50] # Estoque inicial para novos itens
        }
        modelo_df = pd.DataFrame(modelo_data)
        
        # Converte o DataFrame para CSV em memória
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
                        # Converte o DataFrame em uma lista de dicionários para o Supabase
                        registros = df_upload.to_dict(orient='records')
                        
                        # A função 'upsert' é perfeita para isso:
                        # - Se o 'id' existe, atualiza o registro.
                        # - Se o 'id' não existe (ou está em branco), cria um novo registro.
                        response = supabase_client.table('produtos').upsert(registros, on_conflict='id').execute()

                        if response.data:
                            num_registros = len(response.data)
                            st.success(f"Operação concluída com sucesso! {num_registros} registros foram processados.")
                            st.cache_data.clear()
                        else:
                             st.error(f"Erro ao processar o arquivo: {response.error.message if response.error else 'Erro desconhecido'}")
            
            except Exception as e:
                st.error(f"Erro ao ler o arquivo CSV. Verifique o formato e o separador (deve ser ponto e vírgula ';'). Detalhes: {e}")
