import streamlit as st

@st.cache_data(ttl=60)
def get_lista_produtos(supabase_client):
    response = supabase_client.table('produtos').select('id, nome').order('nome').execute()
    return response.data

def registrar_movimentacao(supabase_client, id_produto, tipo, quantidade):
    response = supabase_client.rpc('atualizar_estoque', {
        'produto_id': id_produto, 'quantidade_movimentada': quantidade, 'tipo_mov': tipo
    }).execute()
    
    resultado = response.data
    if resultado == 'Sucesso':
        return True, "Movimentação registrada com sucesso!"
    else:
        return False, resultado

def render_page(supabase_client):
    st.title("🚚 Movimentação de Estoque")

    lista_produtos = get_lista_produtos(supabase_client)
    produtos_dict = {produto['nome']: produto['id'] for produto in lista_produtos}

    if not produtos_dict:
        st.warning("Nenhum produto cadastrado. Adicione produtos primeiro.")
    else:
        produto_selecionado_nome = st.selectbox("Selecione o Produto", options=produtos_dict.keys())
        
        if produto_selecionado_nome:
            id_produto_selecionado = produtos_dict[produto_selecionado_nome]
            col1, col2 = st.columns(2)
            with col1:
                tipo_movimentacao = st.radio("Tipo de Movimentação", ('ENTRADA', 'SAÍDA'), horizontal=True)
            with col2:
                quantidade = st.number_input("Quantidade", min_value=1, step=1)

            if st.button(f"Registrar {tipo_movimentacao}", use_container_width=True, type="primary"):
                with st.spinner("Processando..."):
                    sucesso, mensagem = registrar_movimentacao(supabase_client, id_produto_selecionado, tipo_movimentacao, quantidade)
                    if sucesso:
                        st.success(mensagem)
                        st.cache_data.clear()
                    else:
                        st.error(mensagem)
