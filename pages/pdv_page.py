# pages/pdv_page.py
import streamlit as st
from supabase import Client

# A função de cache foi completamente removida para garantir estabilidade.
def get_produtos_pdv(supabase_client: Client):
    """Busca produtos com estoque positivo usando a conexão fornecida."""
    # Verificação para garantir que a função não é chamada sem a conexão.
    if not supabase_client:
        st.error("Erro interno: a função de busca de produtos foi chamada sem uma conexão válida.")
        return []
    try:
        response = supabase_client.table('produtos').select('id, nome, preco_venda, foto_url, estoque_atual').gt('estoque_atual', 0).order('nome').execute()
        return response.data
    except Exception as e:
        st.error(f"Não foi possível carregar os produtos: {e}")
        return []

def finalizar_venda(supabase_client: Client, carrinho: dict):
    """Processa a finalização da venda, dando baixa no estoque."""
    erros = []
    with st.spinner("Processando Venda..."):
        for item_id, item_data in carrinho.items():
            response = supabase_client.rpc('atualizar_estoque', {
                'produto_id': item_id, 'quantidade_movimentada': item_data['quantidade'], 'tipo_mov': 'SAÍDA'
            }).execute()
            if response.data != 'Sucesso':
                erros.append(f"Produto {item_data['nome']}: {response.data}")

    if erros:
        st.error("A venda não pôde ser completada:\n- " + "\n- ".join(erros))
    else:
        st.success("Venda registrada com sucesso!")
        st.session_state.carrinho = {}
        st.rerun()

def adicionar_ao_carrinho(produto: dict):
    """Adiciona um produto ao carrinho no estado da sessão."""
    id_produto = produto['id']
    if id_produto in st.session_state.carrinho:
        st.session_state.carrinho[id_produto]['quantidade'] += 1
    else:
        st.session_state.carrinho[id_produto] = {
            "nome": produto['nome'],
            "quantidade": 1,
            "preco_unitario": produto['preco_venda']
        }
    st.rerun()

def render_page(supabase_client: Client):
    """Renderiza a página completa do Ponto de Venda."""
    st.title("🛒 Ponto de Venda (PDV)")

    # Verificação principal para garantir que a página recebeu a conexão.
    if not supabase_client:
        st.error("A página do PDV não recebeu a conexão com o banco de dados do painel principal.")
        st.stop()

    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = {}

    col_produtos, col_carrinho = st.columns([3, 1.5])

    with col_produtos:
        st.subheader("Catálogo de Produtos")
        if st.button("🔄 Recarregar Produtos"):
            st.rerun()
        
        produtos = get_produtos_pdv(supabase_client)
        
        num_cols = 4
        cols = st.columns(num_cols)
        
        if not produtos:
            st.warning("Nenhum produto com estoque disponível encontrado.")
        
        for i, produto in enumerate(produtos):
            with cols[i % num_cols]:
                with st.container(border=True):
                    st.image(produto['foto_url'] or "https://placehold.co/300x200?text=Sem+Imagem")
                    st.subheader(f"{produto['nome']}")
                    st.write(f"**R$ {produto['preco_venda']:.2f}**")
                    st.button(
                        "Adicionar",
                        key=f"add_{produto['id']}",
                        on_click=adicionar_ao_carrinho,
                        args=(produto,),
                        use_container_width=True
                    )

    with col_carrinho:
        st.subheader("Carrinho de Compras")
        total_venda = 0
        
        if not st.session_state.carrinho:
            st.info("O carrinho está vazio.")
        else:
            for item_id, item_data in list(st.session_state.carrinho.items()):
                subtotal = item_data['quantidade'] * item_data['preco_unitario']
                total_venda += subtotal

                c1, c2, c3 = st.columns([0.5, 0.3, 0.2])
                with c1:
                    st.write(f"**{item_data['nome']}**")
                    st.write(f"R$ {subtotal:.2f}")
                with c2:
                    nova_qtd = st.number_input("Qtd.", min_value=1, value=item_data['quantidade'], key=f"qtd_{item_id}", label_visibility="collapsed")
                    if nova_qtd != item_data['quantidade']:
                        st.session_state.carrinho[item_id]['quantidade'] = nova_qtd
                        st.rerun()
                with c3:
                    if st.button("❌", key=f"del_{item_id}", help="Remover item"):
                        del st.session_state.carrinho[item_id]
                        st.rerun()
            
            st.divider()
            st.metric("TOTAL DA VENDA", f"R$ {total_venda:.2f}")

            if st.button("💳 Finalizar Venda", use_container_width=True, type="primary", disabled=(not st.session_state.carrinho)):
                finalizar_venda(supabase_client, st.session_state.carrinho)
