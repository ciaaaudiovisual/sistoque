# pages/pdv_page.py
import streamlit as st
from supabase import Client
import traceback

# A abordagem foi reestruturada usando uma classe para gerir o estado e as ações,
# tornando o código mais robusto contra problemas de cache do Streamlit.

class PontoDeVendaApp:
    """
    Classe para encapsular toda a lógica da página do Ponto de Venda (PDV).
    """
    def __init__(self, supabase_client: Client):
        """Inicializa a aplicação do PDV com a conexão do Supabase."""
        if not isinstance(supabase_client, Client):
            st.error("Erro Crítico: A página do PDV não recebeu uma conexão válida.")
            # Lança uma exceção para interromper a execução se a conexão for inválida.
            raise TypeError("O cliente Supabase fornecido é inválido.")
        
        self.supabase = supabase_client
        
        # Garante que o carrinho de compras existe no estado da sessão.
        if 'pdv_carrinho' not in st.session_state:
            st.session_state.pdv_carrinho = {}

    def _adicionar_ao_carrinho(self, produto: dict):
        """Adiciona um item ao carrinho ou incrementa a sua quantidade."""
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
        st.rerun()

    def _remover_do_carrinho(self, id_produto: int):
        """Remove um item do carrinho."""
        if id_produto in st.session_state.pdv_carrinho:
            del st.session_state.pdv_carrinho[id_produto]
            st.rerun()

    def _atualizar_quantidade(self, id_produto: int, nova_quantidade: int):
        """Atualiza a quantidade de um item específico no carrinho."""
        if id_produto in st.session_state.pdv_carrinho:
            st.session_state.pdv_carrinho[id_produto]['quantidade'] = nova_quantidade
            st.rerun()

    def _finalizar_venda(self):
        """Processa a venda, regista as movimentações e limpa o carrinho."""
        carrinho = st.session_state.pdv_carrinho
        erros = []
        with st.spinner("A processar a Venda..."):
            for item_id, item_data in carrinho.items():
                try:
                    # Chama a função RPC 'atualizar_estoque' para cada item.
                    response = self.supabase.rpc('atualizar_estoque', {
                        'produto_id': item_id, 
                        'quantidade_movimentada': item_data['quantidade'], 
                        'tipo_mov': 'SAÍDA'
                    }).execute()
                    # Verifica se a RPC retornou um erro.
                    if response.data != 'Sucesso':
                        erros.append(f"Produto {item_data['nome']}: {response.data}")
                except Exception as e:
                    erros.append(f"Produto {item_data['nome']}: Erro de comunicação com o banco de dados.")
        
        if erros:
            st.error("A venda não pôde ser completada:\n- " + "\n- ".join(erros))
        else:
            st.success("Venda registada com sucesso!")
            st.session_state.pdv_carrinho = {}
            st.rerun()

    def _renderizar_catalogo(self):
        """Busca e exibe os produtos disponíveis para venda."""
        st.subheader("Catálogo de Produtos")
        if st.button("🔄 Recarregar Produtos"):
            st.rerun()

        try:
            # A busca de dados é feita diretamente aqui, sem funções externas em cache.
            response = self.supabase.table('produtos').select(
                'id, nome, preco_venda, foto_url, estoque_atual'
            ).gt('estoque_atual', 0).order('nome').execute()
            produtos = response.data
        except Exception as e:
            st.error("Não foi possível carregar os produtos do catálogo.")
            st.code(traceback.format_exc()) # Mostra o erro detalhado para depuração.
            return

        if not produtos:
            st.warning("Nenhum produto com estoque disponível foi encontrado.")
            return

        num_cols = 4
        cols = st.columns(num_cols)
        for i, produto in enumerate(produtos):
            with cols[i % num_cols]:
                with st.container(border=True):
                    st.image(produto['foto_url'] or "https://placehold.co/300x200?text=Sem+Imagem")
                    st.subheader(f"{produto['nome']}")
                    st.write(f"**R$ {produto['preco_venda']:.2f}**")
                    st.button(
                        "Adicionar",
                        key=f"add_{produto['id']}",
                        on_click=self._adicionar_ao_carrinho,
                        args=(produto,),
                        use_container_width=True
                    )
    
    def _renderizar_carrinho(self):
        """Exibe o carrinho de compras e as suas opções."""
        st.subheader("Carrinho de Compras")
        carrinho = st.session_state.pdv_carrinho

        if not carrinho:
            st.info("O carrinho está vazio.")
            return

        total_venda = 0
        for item_id, item_data in list(carrinho.items()):
            subtotal = item_data['quantidade'] * item_data['preco_unitario']
            total_venda += subtotal
            
            c1, c2, c3 = st.columns([0.6, 0.25, 0.15])
            with c1:
                st.write(f"**{item_data['nome']}** (R$ {subtotal:.2f})")
            with c2:
                nova_qtd = st.number_input(
                    "Qtd.", min_value=1, value=item_data['quantidade'], 
                    key=f"qtd_{item_id}", label_visibility="collapsed"
                )
                if nova_qtd != item_data['quantidade']:
                    self._atualizar_quantidade(item_id, nova_qtd)
            with c3:
                st.button("❌", key=f"del_{item_id}", help="Remover item", on_click=self._remover_do_carrinho, args=(item_id,))
        
        st.divider()
        st.metric("TOTAL DA VENDA", f"R$ {total_venda:.2f}")

        if st.button("💳 Finalizar Venda", use_container_width=True, type="primary"):
            self._finalizar_venda()

    def render(self):
        """Renderiza a página completa do PDV."""
        st.title("🛒 Ponto de Venda (PDV)")
        col_produtos, col_carrinho = st.columns([3, 1.5])

        with col_produtos:
            self._renderizar_catalogo()

        with col_carrinho:
            self._renderizar_carrinho()


# Esta é a única função que o dashboard.py irá chamar.
# Ela cria uma instância da nossa aplicação e a executa.
def render_page(supabase_client: Client):
    try:
        app = PontoDeVendaApp(supabase_client)
        app.render()
    except TypeError as e:
        st.error(f"Erro ao inicializar a página do PDV: {e}")
    except Exception as e:
        st.error("Ocorreu um erro inesperado na página do PDV.")
        st.code(traceback.format_exc())

