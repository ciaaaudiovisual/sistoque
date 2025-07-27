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
        st.subheader("Todos os Produtos")
        df_produtos = get_produtos(supabase_client)

        if not df_produtos.empty:
            df_editado = st.data_editor(
                df_produtos,
                column_config={
                    "id": st.column_config.Column("ID", disabled=True),
                    "foto_url": st.column_config.ImageColumn("Foto"),
                    "nome": "Nome",
                    "tipo": "Categoria",
                    "codigo_barras": "Código de Barras",
                    "preco_compra": st.column_config.NumberColumn("Preço Compra", format="R$ %.2f"),
                    "preco_venda": st.column_config.NumberColumn("Preço Venda", format="R$ %.2f"),
                    "estoque_atual": st.column_config.NumberColumn("Estoque Atual"),
                    "qtd_minima_estoque": st.column_config.NumberColumn("Estoque Mínimo"),
                },
                hide_index=True, use_container_width=True, num_rows="dynamic", key="editor_produtos"
            )
            
            if st.button("Salvar Alterações"):
                with st.spinner("Salvando..."):
                    # Lógica para atualizar/deletar (simplificada, pode ser otimizada)
                    originais = df_produtos.set_index('id').to_dict('index')
                    editados = df_editado.set_index('id').to_dict('index')

                    for prod_id, prod_data in editados.items():
                        if prod_id in originais and prod_data != originais[prod_id]:
                            supabase_client.table('produtos').update(prod_data).eq('id', prod_id).execute()

                    ids_deletados = set(originais.keys()) - set(editados.keys())
                    if ids_deletados:
                        for prod_id in ids_deletados:
                            supabase_client.table('produtos').delete().eq('id', prod_id).execute()
                    
                    st.success("Alterações salvas com sucesso!")
                    st.cache_data.clear()
                    st.rerun()
        else:
            st.info("Nenhum produto cadastrado ainda.")
    
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
