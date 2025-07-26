# pages/pdv_page.py
import streamlit as st
from supabase import Client
import traceback

class PontoDeVendaApp:
    """
    Uma versão avançada do PDV com múltiplos modos de visualização (Grelha e Lista)
    e uma interface de operador mais refinada e eficiente.
    """
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
        # NOVO: Estado para controlar o modo de visualização do catálogo
        if 'pdv_view_mode' not in st.session_state:
            st.session_state.pdv_view_mode = "Grelha" # "Grelha" ou "Lista"

    @st.cache_data(ttl=60, hash_funcs={Client: lambda c: id(c)})
    def get_products_and_categories(_self, supabase_client: Client):
        """Busca todos os produtos e categorias de uma só vez."""
        try:
            response = supabase_client.table('produtos').select(
                'id, nome, preco_venda, estoque_atual, tipo, foto_url'
            ).gt('estoque_atual', 0).limit(1000).execute()
            produtos = response.data
            categorias = ["Todos"] + sorted(list(set([p['tipo'] for p in produtos if p['tipo']])))
            return produtos, categorias
        except Exception as e:
            st.error(f"Não foi possível carregar os produtos: {e}")
            return [], ["Todos"]

    # --- Funções de controlo do carrinho ---
    def _incrementar_quantidade(self, id_produto: int):
        if id_produto in st.session_state.pdv_carrinho:
            st.session_state.pdv_carrinho[id_produto]['quantidade'] += 1

    def _decrementar_quantidade(self, id_produto: int):
        if id_produto in st.session_state.pdv_carrinho:
            st.session_state.pdv_carrinho[id_produto]['quantidade'] -= 1
            if st.session_state.pdv_carrinho[id_produto]['quantidade'] <= 0:
                del st.session_state.pdv_carrinho[id_produto]

    def _adicionar_ao_carrinho(self, produto: dict):
        id_produto = produto['id']
        carrinho = st.session_state.pdv_carrinho
        if id_produto in carrinho:
            self._incrementar_quantidade(id_produto)
        else:
            carrinho[id_produto] = {"nome": produto['nome'], "quantidade": 1, "preco_unitario": produto['preco_venda']}

    def _remover_do_carrinho(self, id_produto: int):
        if id_produto in st.session_state.pdv_carrinho:
            del st.session_state.pdv_carrinho[id_produto]

    def _finalizar_venda(self, forma_pagamento: str):
        # (Lógica interna de finalização permanece a mesma)
        carrinho = st.session_state.pdv_carrinho; erros = []
        with st.spinner("Registrando Venda..."):
            for item_id, item_data in carrinho.items():
                try:
                    response = self.supabase.rpc('atualizar_estoque', {'p_produto_id': item_id, 'p_quantidade_movimentada': item_data['quantidade'], 'p_tipo_mov': 'SAÍDA', 'p_forma_pagamento': forma_pagamento}).execute()
                    if response.data != 'Sucesso': erros.append(f"Produto {item_data['nome']}: {response.data}")
                except Exception as e: erros.append(f"Produto {item_data['nome']}: Erro de comunicação - {e}")
        if erros: st.error("A venda não pôde ser completada:\n- " + "\n- ".join(erros))
        else:
            st.success("Venda registrada com sucesso!"); st.session_state.pdv_carrinho = {}; st.session_state.payment_step = False; st.cache_data.clear(); st.rerun()

    # --- Funções de Renderização da UI ---
    def _renderizar_categorias(self, categorias):
        st.sidebar.title("Categorias")
        categoria_selecionada = st.sidebar.radio("Filtre por categoria:", options=categorias, key="pdv_categoria_radio", label_visibility="collapsed")
        if st.session_state.pdv_categoria_selecionada != categoria_selecionada:
            st.session_state.pdv_categoria_selecionada = categoria_selecionada; st.rerun()

    def _renderizar_catalogo_grelha(self, produtos_filtrados):
        """Renderiza os produtos no modo de visualização em grelha."""
        cols = st.columns(4)
        for i, produto in enumerate(produtos_filtrados):
            col = cols[i % 4]
            with col:
                st.image(produto['foto_url'] or "https://placehold.co/300x200/f0f2f6/777?text=Sem+Imagem")
                st.subheader(produto['nome'])
                c1, c2 = st.columns([1, 2])
                c1.markdown(f"**R$ {produto['preco_venda']:.2f}**")
                c2.button("Adicionar", key=f"add_grid_{produto['id']}", on_click=self._adicionar_ao_carrinho, args=(produto,), use_container_width=True)

    def _renderizar_catalogo_lista(self, produtos_filtrados):
        """Renderiza os produtos no modo de visualização em lista horizontal."""
        with st.container(height=500):
            for produto in produtos_filtrados:
                col_nome, col_preco, col_btn = st.columns([4, 2, 2])
                with col_nome: st.write(produto['nome'])
                with col_preco: st.write(f"R$ {produto['preco_venda']:.2f}")
                with col_btn: st.button("Adicionar", key=f"add_list_{produto['id']}", on_click=self._adicionar_ao_carrinho, args=(produto,), use_container_width=True)
                st.divider()

    def _renderizar_catalogo(self, produtos, categoria_selecionada):
        """Renderiza o cabeçalho do catálogo e o modo de visualização selecionado."""
        header_cols = st.columns([3, 1, 1])
        with header_cols[0]: st.header("Catálogo de Produtos")
        # --- NOVO: Botões para alternar a visualização ---
        with header_cols[1]:
            if st.button("Grelha 🖼️", use_container_width=True, type="secondary" if st.session_state.pdv_view_mode != "Grelha" else "primary"):
                st.session_state.pdv_view_mode = "Grelha"
        with header_cols[2]:
            if st.button("Lista 📜", use_container_width=True, type="secondary" if st.session_state.pdv_view_mode != "Lista" else "primary"):
                st.session_state.pdv_view_mode = "Lista"

        produtos_filtrados = [p for p in produtos if p['tipo'] == categoria_selecionada] if categoria_selecionada != "Todos" else produtos
        if not produtos_filtrados: st.info("Nenhum produto encontrado nesta categoria."); return

        if st.session_state.pdv_view_mode == "Grelha":
            self._renderizar_catalogo_grelha(produtos_filtrados)
        else:
            self._renderizar_catalogo_lista(produtos_filtrados)

    def _renderizar_carrinho(self):
        st.header("Carrinho")
        if not st.session_state.pdv_carrinho: st.info("O carrinho está vazio."); st.session_state.payment_step = False; return

        total_venda = 0
        with st.container(border=True):
            for item_id, item_data in list(st.session_state.pdv_carrinho.items()):
                subtotal = item_data['quantidade'] * item_data['preco_unitario']; total_venda += subtotal
                col_info, col_qtd, col_remove = st.columns([4, 3, 1])
                with col_info: st.write(f"**{item_data['nome']}**"); st.caption(f"R$ {subtotal:.2f}")
                with col_qtd:
                    q_c1, q_c2, q_c3 = st.columns([1, 1, 1])
                    q_c1.button("−", key=f"dec_{item_id}", on_click=self._decrementar_quantidade, args=(item_id,), use_container_width=True)
                    q_c2.write(f"<div style='text-align: center; padding-top: 5px;'>{item_data['quantidade']}</div>", unsafe_allow_html=True)
                    q_c3.button("+", key=f"inc_{item_id}", on_click=self._incrementar_quantidade, args=(item_id,), use_container_width=True)
                with col_remove: st.button("🗑️", key=f"del_{item_id}", help="Remover item", on_click=self._remover_do_carrinho, args=(item_id,), use_container_width=True)
                st.divider()
        
        st.subheader(f"TOTAL: R$ {total_venda:.2f}")

        if not st.session_state.payment_step:
            if st.button("Prosseguir para Pagamento", use_container_width=True, type="primary"): st.session_state.payment_step = True; st.rerun()
        else:
            st.markdown("##### Selecione a Forma de Pagamento")
            forma_pagamento = st.selectbox("Forma de Pagamento", ["Dinheiro", "Cartão de Débito", "Cartão de Crédito", "PIX", "Outro"], label_visibility="collapsed")
            if st.button(f"Confirmar Venda em {forma_pagamento}", use_container_width=True, type="primary"): self._finalizar_venda(forma_pagamento)
            if st.button("Voltar ao Carrinho", use_container_width=True): st.session_state.payment_step = False; st.rerun()

    def render(self):
        st.title("Ponto de Venda (PDV)")
        produtos, categorias = self.get_products_and_categories(self.supabase)
        self._renderizar_categorias(categorias)
        col_catalogo, col_carrinho = st.columns([2, 1])
        with col_catalogo:
            if st.session_state.payment_step: st.info("Finalize a venda atual para iniciar uma nova.")
            else: self._renderizar_catalogo(produtos, st.session_state.pdv_categoria_selecionada)
        with col_carrinho: self._renderizar_carrinho()

def render_page(supabase_client: Client):
    try:
        st.markdown("""<style>[data-testid="stSidebarNav"] {display: none;}</style>""", unsafe_allow_html=True)
        app = PontoDeVendaApp(supabase_client)
        app.render()
    except Exception as e:
        st.error("Ocorreu um erro crítico na página do PDV."); st.code(traceback.format_exc())
