# pages/pdv_page.py
import streamlit as st
from supabase import Client
import traceback

class PontoDeVendaApp:
    """
    Classe para encapsular a nova lógica da página do Ponto de Venda (PDV)
    com um layout mais compacto e profissional.
    """
    def __init__(self, supabase_client: Client):
        if not isinstance(supabase_client, Client):
            raise TypeError("O cliente Supabase fornecido é inválido.")
        
        self.supabase = supabase_client
        
        if 'pdv_carrinho' not in st.session_state:
            st.session_state.pdv_carrinho = {}
        if 'pdv_search_query' not in st.session_state:
            st.session_state.pdv_search_query = ""

    def _adicionar_ao_carrinho(self, produto: dict):
        id_produto = produto['id']
        carrinho = st.session_state.pdv_carrinho
        if id_produto in carrinho:
            carrinho[id_produto]['quantidade'] += 1
        else:
            carrinho[id_produto] = {
                "nome": produto['nome'],
                "quantidade": 1,
                "preco_unitario": produto['preco_venda']
            }

    def _remover_do_carrinho(self, id_produto: int):
        if id_produto in st.session_state.pdv_carrinho:
            del st.session_state.pdv_carrinho[id_produto]
            st.rerun()

    def _atualizar_quantidade(self, id_produto: int):
        nova_quantidade = st.session_state[f"qtd_{id_produto}"]
        if id_produto in st.session_state.pdv_carrinho:
            st.session_state.pdv_carrinho[id_produto]['quantidade'] = nova_quantidade

    def _finalizar_venda(self):
        carrinho = st.session_state.pdv_carrinho
        erros = []
        with st.spinner("A processar a Venda..."):
            for item_id, item_data in carrinho.items():
                try:
                    response = self.supabase.rpc('atualizar_estoque', {
                        'p_produto_id': item_id, 
                        'p_quantidade_movimentada': item_data['quantidade'], 
                        'p_tipo_mov': 'SAÍDA'
                    }).execute()
                    if response.data != 'Sucesso':
                        erros.append(f"Produto {item_data['nome']}: {response.data}")
                except Exception as e:
                    erros.append(f"Produto {item_data['nome']}: Erro de comunicação - {e}")
        
        if erros:
            st.error("A venda não pôde ser completada:\n- " + "\n- ".join(erros))
        else:
            st.success("Venda registada com sucesso!")
            st.session_state.pdv_carrinho = {}
            st.rerun()

    def _renderizar_catalogo(self):
        st.subheader("Adicionar Produtos")

        # --- NOVO: Barra de pesquisa ---
        st.text_input(
            "Pesquisar produto por nome", 
            key="pdv_search_query",
            placeholder="Digite o nome do produto..."
        )
        query = st.session_state.pdv_search_query

        try:
            response = self.supabase.table('produtos').select(
                'id, nome, preco_venda, estoque_atual'
            ).gt('estoque_atual', 0).order('nome').execute()
            produtos = response.data
        except Exception as e:
            st.error(f"Não foi possível carregar os produtos do catálogo: {e}")
            return

        # --- NOVO: Filtrar produtos com base na pesquisa ---
        if query:
            produtos_filtrados = [
                p for p in produtos if query.lower() in p['nome'].lower()
            ]
        else:
            produtos_filtrados = produtos

        if not produtos_filtrados:
            st.info("Nenhum produto encontrado.")
            return

        # --- NOVO: Layout em lista compacta ---
        list_container = st.container(height=400, border=False)
        with list_container:
            # Cabeçalho da lista
            c1, c2, c3 = st.columns([4, 2, 1.5])
            c1.markdown("**Produto**")
            c2.markdown("**Preço**")
            c3.markdown("**Ação**")
            st.divider()

            for produto in produtos_filtrados:
                col1, col2, col3 = st.columns([4, 2, 1.5])
                with col1:
                    st.write(produto['nome'])
                with col2:
                    st.write(f"R$ {produto['preco_venda']:.2f}")
                with col3:
                    st.button(
                        "Adicionar", 
                        key=f"add_{produto['id']}",
                        on_click=self._adicionar_ao_carrinho, 
                        args=(produto,),
                        use_container_width=True
                    )
                st.divider()
    
    def _renderizar_carrinho(self):
        st.subheader("Resumo da Venda")
        carrinho = st.session_state.pdv_carrinho

        if not carrinho:
            st.info("O carrinho está vazio.")
            return

        # --- NOVO: Layout do carrinho mais limpo ---
        cart_container = st.container(height=350, border=False)
        with cart_container:
            total_venda = 0
            for item_id, item_data in list(carrinho.items()):
                subtotal = item_data['quantidade'] * item_data['preco_unitario']
                total_venda += subtotal
                
                c1, c2, c3 = st.columns([5, 2, 1])
                with c1:
                    st.write(f"**{item_data['nome']}**")
                    st.caption(f"{item_data['quantidade']} un x R$ {item_data['preco_unitario']:.2f} = R$ {subtotal:.2f}")
                with c2:
                    st.number_input(
                        "Qtd.", min_value=1,
                        key=f"qtd_{item_id}",
                        value=item_data['quantidade'],
                        on_change=self._atualizar_quantidade,
                        args=(item_id,),
                        label_visibility="collapsed"
                    )
                with c3:
                    st.button("❌", key=f"del_{item_id}", help="Remover item", 
                              on_click=self._remover_do_carrinho, args=(item_id,),
                              use_container_width=True)
                st.divider()
        
        st.subheader(f"TOTAL: R$ {total_venda:.2f}")

        if st.button("💳 Finalizar Venda", use_container_width=True, type="primary", disabled=(not carrinho)):
            self._finalizar_venda()

    def render(self):
        st.title("🛒 Ponto de Venda (PDV)")
        col_produtos, col_carrinho = st.columns([1.5, 1])

        with col_produtos:
            self._renderizar_catalogo()

        with col_carrinho:
            self._renderizar_carrinho()

def render_page(supabase_client: Client):
    try:
        app = PontoDeVendaApp(supabase_client)
        app.render()
    except Exception as e:
        st.error("Ocorreu um erro crítico na página do PDV.")
        st.code(traceback.format_exc())
