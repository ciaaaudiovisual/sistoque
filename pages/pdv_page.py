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
        if 'pdv_search_query' not in st.session_state:
            st.session_state.pdv_search_query = ""
        # NOVO: Estado para controlar a etapa de pagamento
        if 'payment_step' not in st.session_state:
            st.session_state.payment_step = False

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

    # --- FUNÇÃO DE FINALIZAÇÃO MODIFICADA ---
    def _finalizar_venda(self, forma_pagamento: str):
        carrinho = st.session_state.pdv_carrinho
        erros = []
        with st.spinner("Registrando Venda..."):
            for item_id, item_data in carrinho.items():
                try:
                    # Agora passa a forma de pagamento para a função do banco de dados
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
            # Reseta os estados
            st.session_state.pdv_carrinho = {}
            st.session_state.payment_step = False
            st.cache_data.clear()
            st.rerun()

    def _renderizar_catalogo(self):
        st.subheader("Adicionar Produtos")
        st.text_input("Pesquisar produto por nome", key="pdv_search_query", placeholder="Digite para pesquisar...")
        query = st.session_state.pdv_search_query

        try:
            response = self.supabase.table('produtos').select('id, nome, preco_venda, estoque_atual').gt('estoque_atual', 0).order('nome').execute()
            produtos = response.data
        except Exception as e:
            st.error(f"Não foi possível carregar os produtos: {e}")
            return

        produtos_filtrados = [p for p in produtos if query.lower() in p['nome'].lower()] if query else produtos

        if not produtos_filtrados:
            st.info("Nenhum produto encontrado.")
            return

        with st.container(height=400, border=False):
            c1, c2, c3 = st.columns([4, 2, 1.5]); c1.markdown("**Produto**"); c2.markdown("**Preço**"); c3.markdown("**Ação**")
            st.divider()
            for produto in produtos_filtrados:
                col1, col2, col3 = st.columns([4, 2, 1.5])
                col1.write(produto['nome'])
                col2.write(f"R$ {produto['preco_venda']:.2f}")
                col3.button("Adicionar", key=f"add_{produto['id']}", on_click=self._adicionar_ao_carrinho, args=(produto,), use_container_width=True)
                st.divider()
    
    def _renderizar_carrinho(self):
        st.subheader("Resumo da Venda")
        carrinho = st.session_state.pdv_carrinho

        if not carrinho:
            st.info("O carrinho está vazio.")
            st.session_state.payment_step = False # Garante que a etapa de pagamento seja ocultada
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

        # --- LÓGICA DE PAGAMENTO MODIFICADA ---
        # Se não estiver na etapa de pagamento, mostra o botão para iniciar
        if not st.session_state.payment_step:
            if st.button("Prosseguir para Pagamento", use_container_width=True, type="primary"):
                st.session_state.payment_step = True
                st.rerun()
        # Se estiver na etapa de pagamento, mostra as opções
        else:
            st.markdown("##### Selecione a Forma de Pagamento")
            forma_pagamento = st.selectbox(
                "Forma de Pagamento",
                ["Dinheiro", "Cartão de Débito", "Cartão de Crédito", "PIX", "Outro"],
                label_visibility="collapsed"
            )
            
            # Botão para confirmar a venda com a forma de pagamento
            if st.button(f"Confirmar Venda em {forma_pagamento}", use_container_width=True, type="primary"):
                self._finalizar_venda(forma_pagamento)

            # Botão para cancelar e voltar ao carrinho
            if st.button("Cancelar", use_container_width=True):
                st.session_state.payment_step = False
                st.rerun()

    def render(self):
        st.title("🛒 Ponto de Venda (PDV)")
        # Desabilita o catálogo durante a etapa de pagamento para evitar erros
        col_produtos, col_carrinho = st.columns([1.5, 1])
        with col_produtos:
            with st.expander("Catálogo de Produtos", expanded=not st.session_state.payment_step):
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
