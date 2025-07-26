# pages/pdv_page.py
import streamlit as st
from supabase import Client
import traceback

class PontoDeVendaApp:
    def __init__(self, supabase_client: Client):
        if not isinstance(supabase_client, Client):
            raise TypeError("O cliente Supabase fornecido é inválido.")
        self.supabase = supabase_client
        
        # Inicializa os estados da sessão
        if 'pdv_carrinho' not in st.session_state:
            st.session_state.pdv_carrinho = {}
        if 'pdv_categoria_selecionada' not in st.session_state:
            st.session_state.pdv_categoria_selecionada = "Todos"
        if 'payment_step' not in st.session_state:
            st.session_state.payment_step = False

    @st.cache_data(ttl=60, hash_funcs={Client: lambda c: id(c)})
    def get_products_and_categories(_self, supabase_client: Client):
        """Busca todos os produtos e categorias de uma só vez."""
        try:
            # Aumenta o limite para garantir que todos os produtos sejam retornados
            response = supabase_client.table('produtos').select('id, nome, preco_venda, estoque_atual, tipo, foto_url').gt('estoque_atual', 0).limit(1000).execute()
            produtos = response.data
            categorias = ["Todos"] + sorted(list(set([p['tipo'] for p in produtos if p['tipo']])))
            return produtos, categorias
        except Exception as e:
            st.error(f"Não foi possível carregar os produtos: {e}")
            return [], ["Todos"]

    def _adicionar_ao_carrinho(self, produto: dict):
        id_produto = produto['id']
        carrinho = st.session_state.pdv_carrinho
        if id_produto in carrinho:
            carrinho[id_produto]['quantidade'] += 1
        else:
            carrinho[id_produto] = {"nome": produto['nome'], "quantidade": 1, "preco_unitario": produto['preco_venda']}

    def _remover_do_carrinho(self, id_produto: int):
        if id_produto in st.session_state.pdv_carrinho:
            del st.session_state.pdv_carrinho[id_produto]
            st.rerun()

    def _atualizar_quantidade(self, id_produto: int):
        nova_quantidade = st.session_state[f"qtd_{id_produto}"]
        if id_produto in st.session_state.pdv_carrinho:
            st.session_state.pdv_carrinho[id_produto]['quantidade'] = nova_quantidade

    def _finalizar_venda(self, forma_pagamento: str):
        carrinho = st.session_state.pdv_carrinho
        erros = []
        with st.spinner("Registrando Venda..."):
            for item_id, item_data in carrinho.items():
                try:
                    response = self.supabase.rpc('atualizar_estoque', {
                        'p_produto_id': item_id, 
                        'p_quantidade_movimentada': item_data['quantidade'], 
                        'p_tipo_mov': 'SAÍDA',
                        'p_forma_pagamento': forma_pagamento
                    }).execute()
                    if response.data != 'Sucesso':
                        erros.append(f"Produto {item_data['nome']}: {response.data}")
                except Exception as e:
                    erros.append(f"Produto {item_data['nome']}: Erro de comunicação - {e}")
        
        if erros:
            st.error("A venda não pôde ser completada:\n- " + "\n- ".join(erros))
        else:
            st.success("Venda registrada com sucesso!")
            st.session_state.pdv_carrinho = {}
            st.session_state.payment_step = False
            st.cache_data.clear()
            st.rerun()

    def _renderizar_categorias(self, categorias):
        st.sidebar.title("Categorias")
        categoria_selecionada = st.sidebar.radio(
            "Filtre por categoria:",
            options=categorias,
            key="pdv_categoria_radio"
        )
        st.session_state.pdv_categoria_selecionada = categoria_selecionada


    def _renderizar_catalogo(self, produtos, categoria_selecionada):
        st.header("Catálogo de Produtos")
        
        if categoria_selecionada != "Todos":
            produtos_filtrados = [p for p in produtos if p['tipo'] == categoria_selecionada]
        else:
            produtos_filtrados = produtos

        if not produtos_filtrados:
            st.info("Nenhum produto encontrado nesta categoria.")
            return

        cols = st.columns(4) # Define 4 colunas para a grelha
        for i, produto in enumerate(produtos_filtrados):
            col = cols[i % 4]
            with col:
                with st.container(border=True):
                    st.image(produto['foto_url'] or "https://placehold.co/300x200?text=Sem+Imagem")
                    st.subheader(produto['nome'])
                    st.markdown(f"**R$ {produto['preco_venda']:.2f}**")
                    if st.button("Adicionar", key=f"add_{produto['id']}", use_container_width=True):
                        self._adicionar_ao_carrinho(produto)
                        st.rerun()

    def _renderizar_carrinho(self):
        st.header("Carrinho")
        carrinho = st.session_state.pdv_carrinho

        if not carrinho:
            st.info("O carrinho está vazio.")
            st.session_state.payment_step = False
            return

        with st.container(height=350, border=False):
            total_venda = 0
            for item_id, item_data in list(carrinho.items()):
                subtotal = item_data['quantidade'] * item_data['preco_unitario']
                total_venda += subtotal
                c1, c2, c3 = st.columns([5, 2, 1])
                c1.write(f"**{item_data['nome']}**"); c1.caption(f"{item_data['quantidade']} un x R$ {item_data['preco_unitario']:.2f} = R$ {subtotal:.2f}")
                c2.number_input("Qtd.", min_value=1, key=f"qtd_{item_id}", value=item_data['quantidade'], on_change=self._atualizar_quantidade, args=(item_id,), label_visibility="collapsed")
                c3.button("❌", key=f"del_{item_id}", help="Remover item", on_click=self._remover_do_carrinho, args=(item_id,), use_container_width=True)
                st.divider()
        
        st.subheader(f"TOTAL: R$ {total_venda:.2f}")

        if not st.session_state.payment_step:
            if st.button("Prosseguir para Pagamento", use_container_width=True, type="primary"):
                st.session_state.payment_step = True
                st.rerun()
        else:
            st.markdown("##### Selecione a Forma de Pagamento")
            forma_pagamento = st.selectbox("Forma de Pagamento", ["Dinheiro", "Cartão de Débito", "Cartão de Crédito", "PIX", "Outro"], label_visibility="collapsed")
            if st.button(f"Confirmar Venda em {forma_pagamento}", use_container_width=True, type="primary"):
                self._finalizar_venda(forma_pagamento)
            if st.button("Cancelar", use_container_width=True):
                st.session_state.payment_step = False
                st.rerun()

    def render(self):
        st.title("Ponto de Venda (PDV)")
        
        produtos, categorias = self.get_products_and_categories(self.supabase)
        
        # Layout principal com sidebar para categorias
        self._renderizar_categorias(categorias)
        
        col_catalogo, col_carrinho = st.columns([2, 1])

        with col_catalogo:
            self._renderizar_catalogo(produtos, st.session_state.pdv_categoria_selecionada)
        
        with col_carrinho:
            self._renderizar_carrinho()

def render_page(supabase_client: Client):
    try:
        # Esconde a sidebar principal do Streamlit para usar a nossa própria para categorias
        st.markdown("""<style>[data-testid="stSidebarNav"] {display: none;}</style>""", unsafe_allow_html=True)
        app = PontoDeVendaApp(supabase_client)
        app.render()
    except Exception as e:
        st.error("Ocorreu um erro crítico na página do PDV.")
        st.code(traceback.format_exc())
