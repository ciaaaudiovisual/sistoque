# pages/pdv_page.py
import streamlit as st
from supabase import Client
import traceback
import av
from PIL import Image
from pyzbar.pyzbar import decode
from streamlit_webrtc import webrtc_streamer, WebRtcMode

# Classe para armazenar o resultado do código de barras de forma segura entre execuções
class BarcodeResult:
    def __init__(self):
        self.value = None
    def set(self, value):
        self.value = value
    def get(self):
        return self.value

class PontoDeVendaApp:
    """
    PDV reformulado com layout adaptativo, leitor de código de barras
    e carregamento completo de produtos.
    """
    def __init__(self, supabase_client: Client):
        if not isinstance(supabase_client, Client):
            raise TypeError("O cliente Supabase fornecido é inválido.")
        self.supabase = supabase_client
        
        for key, default_value in [
            ('pdv_carrinho', {}), ('pdv_categoria_selecionada', "Todos"),
            ('payment_step', False), ('pdv_view_mode', "Grelha"),
            ('barcode_result', None), ('show_scanner', False)
        ]:
            if key not in st.session_state:
                st.session_state[key] = default_value

    @st.cache_data(ttl=300, hash_funcs={Client: lambda c: id(c)})
    def get_products_and_categories(_self, supabase_client: Client):
        all_produtos = []
        current_page = 0
        page_size = 1000
        while True:
            try:
                start_index = current_page * page_size
                response = supabase_client.table('produtos').select('id, nome, preco_venda, estoque_atual, tipo, foto_url, codigo_barras').gte('estoque_atual', 0).range(start_index, start_index + page_size - 1).execute()
                
                batch = response.data
                if not batch: break
                all_produtos.extend(batch)
                current_page += 1
            except Exception as e:
                st.error(f"Não foi possível carregar os produtos: {e}")
                return [], ["Todos"]
        categorias = ["Todos"] + sorted(list(set([p['tipo'] for p in all_produtos if p['tipo']])))
        return all_produtos, categorias

    def _find_product_by_barcode(self, barcode_data: str, produtos: list):
        for produto in produtos:
            if produto.get('codigo_barras') == barcode_data:
                return produto
        return None

    def _incrementar_quantidade(self, id_produto: int):
        if id_produto in st.session_state.pdv_carrinho:
            st.session_state.pdv_carrinho[id_produto]['quantidade'] += 1

    def _decrementar_quantidade(self, id_produto: int):
        if id_produto in st.session_state.pdv_carrinho and st.session_state.pdv_carrinho[id_produto]['quantidade'] > 1:
            st.session_state.pdv_carrinho[id_produto]['quantidade'] -= 1
        else:
            self._remover_do_carrinho(id_produto)

    def _adicionar_ao_carrinho(self, produto: dict):
        id_produto = produto['id']
        if id_produto in st.session_state.pdv_carrinho:
            self._incrementar_quantidade(id_produto)
        else:
            st.session_state.pdv_carrinho[id_produto] = {
                "nome": produto['nome'], "quantidade": 1, "preco_unitario": produto['preco_venda']
            }

    def _remover_do_carrinho(self, id_produto: int):
        if id_produto in st.session_state.pdv_carrinho:
            del st.session_state.pdv_carrinho[id_produto]
            if not st.session_state.pdv_carrinho:
                st.session_state.payment_step = False
            st.rerun()

    def _finalizar_venda(self, forma_pagamento: str):
        carrinho, erros = st.session_state.pdv_carrinho, []
        with st.spinner("Registrando Venda..."):
            for item_id, item_data in carrinho.items():
                try:
                    response = self.supabase.rpc('atualizar_estoque', {'p_produto_id': item_id, 'p_quantidade_movimentada': item_data['quantidade'], 'p_tipo_mov': 'SAÍDA', 'p_forma_pagamento': forma_pagamento}).execute()
                    if hasattr(response, 'data') and response.data != 'Sucesso': erros.append(f"Produto {item_data['nome']}: {response.data}")
                except Exception as e: erros.append(f"Produto {item_data['nome']}: Erro de comunicação - {e}")
        if erros: st.error("A venda não pôde ser completada:\n- " + "\n- ".join(erros))
        else: st.success("Venda registrada com sucesso!"); st.session_state.pdv_carrinho = {}; st.session_state.payment_step = False; st.cache_data.clear(); st.rerun()

    def _renderizar_categorias(self, categorias):
        st.sidebar.title("Categorias")
        categoria_selecionada = st.sidebar.radio("Filtre por categoria:", options=categorias, key="pdv_categoria_radio", index=categorias.index(st.session_state.pdv_categoria_selecionada))
        if st.session_state.pdv_categoria_selecionada != categoria_selecionada:
            st.session_state.pdv_categoria_selecionada = categoria_selecionada; st.rerun()

    # --- FUNÇÃO CORRIGIDA ---
    def _renderizar_leitor_codigo_barras(self, produtos, container):
        barcode_result_container = BarcodeResult()
        def video_frame_callback(frame: av.VideoFrame) -> av.VideoFrame:
            img = frame.to_image()
            barcodes = decode(img)
            if barcodes:
                barcode_data = barcodes[0].data.decode('utf-8')
                barcode_result_container.set(barcode_data)
            return frame
        
        # Renderiza o leitor DENTRO do container do diálogo
        webrtc_ctx = container.webrtc_streamer(
            key="barcode-scanner", mode=WebRtcMode.SENDRECV,
            video_frame_callback=video_frame_callback,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True,
        )

        if webrtc_ctx.state.playing and barcode_result_container.get():
            st.session_state.barcode_result = barcode_result_container.get()
            st.session_state.show_scanner = False
            st.rerun()

    def _renderizar_catalogo(self, produtos, categoria_selecionada):
        col_header1, col_header2 = st.columns([1, 1])
        with col_header1: st.header("Catálogo")
        with col_header2: st.button("📷 Ler Código", on_click=lambda: st.session_state.update(show_scanner=True), use_container_width=True)

        is_grelha = st.session_state.pdv_view_mode == "Grelha"
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🖼️ Grelha", use_container_width=True, type="primary" if is_grelha else "secondary"):
                st.session_state.pdv_view_mode = "Grelha"; st.rerun()
        with col_btn2:
            if st.button("📜 Lista", use_container_width=True, type="primary" if not is_grelha else "secondary"):
                st.session_state.pdv_view_mode = "Lista"; st.rerun()
        st.divider()

        produtos_filtrados = [p for p in produtos if p['tipo'] == categoria_selecionada] if categoria_selecionada != "Todos" else produtos
        if not produtos_filtrados: st.info("Nenhum produto encontrado nesta categoria."); return

        if st.session_state.pdv_view_mode == "Grelha": self._renderizar_catalogo_grelha(produtos_filtrados)
        else: self._renderizar_catalogo_lista(produtos_filtrados)

    def _renderizar_catalogo_grelha(self, produtos_filtrados):
        cols = st.columns(4)
    for i, produto in enumerate(produtos_filtrados):
        with cols[i % 4]:
            with st.container(border=True):
                st.image(produto['foto_url'] or "https://placehold.co/300x200/f0f2f6/777?text=Sem+Imagem")
                # Estilo CSS para não quebrar a linha do nome do produto
                st.markdown(f"""
                <div style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{produto['nome']}">
                    <h5 style="margin-bottom: 0;">{produto['nome']}</h5>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(f"**R$ {produto['preco_venda']:.2f}**")
                
                # Condição para mostrar o botão correto baseado no estoque
                if produto.get('estoque_atual', 0) > 0:
                    st.button("Adicionar ＋", key=f"add_grid_{produto['id']}", on_click=self._adicionar_ao_carrinho, args=(produto,), use_container_width=True, type="primary")
                else:
                    st.button("Fora de Estoque", key=f"add_grid_{produto['id']}", use_container_width=True, disabled=True)

    def _renderizar_catalogo_lista(self, produtos_filtrados):
        with st.container(height=600):
            for produto in produtos_filtrados:
                cols = st.columns([3, 1, 1.2])
                with cols[0]: st.write(f"**{produto['nome']}**")
                with cols[1]: st.write(f"R$ {produto['preco_venda']:.2f}")
                with cols[2]: st.button("Adicionar ＋", key=f"add_list_{produto['id']}", on_click=self._adicionar_ao_carrinho, args=(produto,), use_container_width=True)
                st.divider()
    
    def _renderizar_carrinho(self):
        carrinho = st.session_state.pdv_carrinho
        total_venda = sum(item['quantidade'] * item['preco_unitario'] for item in carrinho.values())
        total_itens = sum(item['quantidade'] for item in carrinho.values())
        expander_label = f"🛒 Carrinho ({total_itens} {'item' if total_itens == 1 else 'itens'}) - TOTAL: R$ {total_venda:.2f}"
        
        with st.expander(expander_label, expanded=True):
            if not carrinho: st.info("O carrinho está vazio."); st.session_state.payment_step = False; return
            for item_id, item_data in list(carrinho.items()):
                subtotal = item_data['quantidade'] * item_data['preco_unitario']
                col_info, col_qtd, col_remove = st.columns([4, 3, 1])
                with col_info: st.write(f"**{item_data['nome']}**"); st.caption(f"R$ {subtotal:.2f}")
                with col_qtd:
                    q_c1, q_c2, q_c3 = st.columns([1, 1, 1])
                    q_c1.button("−", key=f"dec_{item_id}", on_click=self._decrementar_quantidade, args=(item_id,), use_container_width=True)
                    q_c2.write(f"<div style='text-align: center; padding-top: 5px;'>{item_data['quantidade']}</div>", unsafe_allow_html=True)
                    q_c3.button("+", key=f"inc_{item_id}", on_click=self._incrementar_quantidade, args=(item_id,), use_container_width=True)
                with col_remove: st.button("🗑️", key=f"del_{item_id}", help="Remover item", on_click=self._remover_do_carrinho, args=(item_id,), use_container_width=True)
            st.divider()
            if not st.session_state.payment_step:
                if st.button("Prosseguir para Pagamento", use_container_width=True, type="primary"): st.session_state.payment_step = True; st.rerun()
            else:
                st.markdown("##### Selecione a Forma de Pagamento"); forma_pagamento = st.selectbox("Forma de Pagamento", ["Dinheiro", "Cartão de Débito", "Cartão de Crédito", "PIX"], label_visibility="collapsed")
                btn_cols = st.columns(2)
                with btn_cols[0]:
                    if st.button(f"Confirmar Venda", use_container_width=True, type="primary"): self._finalizar_venda(forma_pagamento)
                with btn_cols[1]:
                    if st.button("Cancelar", use_container_width=True): st.session_state.payment_step = False; st.rerun()

    def render(self):
        st.set_page_config(layout="wide"); st.title("Ponto de Venda (PDV)")
        produtos, categorias = self.get_products_and_categories(self.supabase)
        self._renderizar_categorias(categorias)

        if st.session_state.barcode_result:
            codigo = st.session_state.barcode_result
            st.session_state.barcode_result = None
            produto_encontrado = self._find_product_by_barcode(codigo, produtos)
            if produto_encontrado:
                self._adicionar_ao_carrinho(produto_encontrado)
                st.toast(f"✅ {produto_encontrado['nome']} adicionado ao carrinho!")
            else:
                st.toast(f"❌ Código '{codigo}' não encontrado!")
            st.rerun()

        # --- CHAMADA CORRIGIDA AO DIALOG ---
        if st.session_state.show_scanner:
            dialog = st.dialog("Leitor de Código de Barras")
            dialog.write("Aponte a câmera para o código de barras do produto.")
            self._renderizar_leitor_codigo_barras(produtos, container=dialog)

        if st.session_state.payment_step: st.info("Finalize ou cancele a venda atual para iniciar uma nova.")
        self._renderizar_carrinho()
        if not st.session_state.payment_step: self._renderizar_catalogo(produtos, st.session_state.pdv_categoria_selecionada)

def render_page(supabase_client: Client):
    try:
        st.markdown("""<style>[data-testid="stSidebarNav"] {display: none;}</style>""", unsafe_allow_html=True)
        app = PontoDeVendaApp(supabase_client)
        app.render()
    except Exception:
        st.error("Ocorreu um erro crítico na página do PDV."); st.code(traceback.format_exc())
