import streamlit as st
from streamlit_option_menu import option_menu
import re
import pandas as pd
from datetime import datetime, timedelta
import pytz  # Importa a biblioteca de fuso horário

# --- CORREÇÃO: Importações necessárias para a função de cache ---
from supabase import Client
from utils import init_connection, supabase_client_hash_func
from pages import gestao_produtos_page, gerenciamento_usuarios_page, movimentacao_page, pdv_page, relatorios_page

st.set_page_config(page_title="Sistoque | Sistema de Gestão", layout="wide")

# --- FUNÇÕES DE DADOS PARA O DASHBOARD ---
# --- CORREÇÃO: Adicionado o hash_funcs para o cliente Supabase ---
@st.cache_data(ttl=60, hash_funcs={Client: supabase_client_hash_func})
def get_dashboard_data(supabase: Client):
    """Busca os dados necessários para o dashboard."""
    produtos_response = supabase.table('produtos').select('*').execute()
    movimentacoes_response = supabase.table('movimentacoes').select('*').eq('tipo_movimentacao', 'SAÍDA').execute()
    
    df_produtos = pd.DataFrame(produtos_response.data)
    df_movimentacoes = pd.DataFrame(movimentacoes_response.data)
    
    return df_produtos, df_movimentacoes

# --- PÁGINA PRINCIPAL ---
def main():
    supabase = init_connection()
    if not supabase:
        st.stop()

    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None

    # --- TELA DE LOGIN ---
    if st.session_state.user is None:
        st.markdown("""<style>[data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)
        st.title("📦 Sistoque | Controle de Estoque e Vendas")
        login_tab, signup_tab = st.tabs(["Entrar", "Cadastre-se"])
        with login_tab:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar"):
                    try:
                        session = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        profile_response = supabase.table('perfis').select('cargo, status, nome_completo').eq('id', session.user.id).single().execute()
                        profile = profile_response.data
                        if profile and profile['status'] == 'Ativo':
                            st.session_state.user = session.user
                            st.session_state.user_role = profile['cargo']
                            st.rerun()
                        elif profile and profile['status'] == 'Pendente':
                            st.warning("Sua conta está aguardando aprovação de um administrador.")
                        else:
                            st.error("Conta inativa ou não confirmada. Verifique seu e-mail.")
                    except Exception:
                        st.error("Falha no login. Verifique seu e-mail e senha.")
        with signup_tab:
            with st.form("signup_form", clear_on_submit=True):
                nome_completo = st.text_input("Nome Completo")
                email_signup = st.text_input("Email de Cadastro")
                password_signup = st.text_input("Crie uma Senha", type="password")
                if st.form_submit_button("Registrar"):
                    if not all([nome_completo, email_signup, password_signup]):
                        st.error("Por favor, preencha todos os campos.")
                    elif not re.match(r"[^@]+@[^@]+\.[^@]+", email_signup):
                        st.error("Formato de e-mail inválido.")
                    else:
                        try:
                            supabase.auth.sign_up({"email": email_signup, "password": password_signup, "options": {"data": {'nome_completo': nome_completo}}})
                            st.success("Cadastro realizado! Verifique seu e-mail para confirmação e aguarde a aprovação do administrador.")
                        except Exception as e:
                            st.error(f"Erro no cadastro: {e}")
        return

    # --- APLICAÇÃO PRINCIPAL PÓS-LOGIN ---
    with st.sidebar:
        st.subheader(f"Bem-vindo(a), {st.session_state.user.user_metadata.get('nome_completo', '')}!")
        st.write(f"Cargo: **{st.session_state.user_role}**")
        if st.button("Sair (Logout)", use_container_width=True):
            st.session_state.user = None
            st.session_state.user_role = None
            st.cache_data.clear()
            st.rerun()

    selected = option_menu(
        menu_title=None,
        options=["Dashboard", "PDV", "Produtos", "Movimentação", "Relatórios", "Usuários"],
        icons=["house-door-fill", "cart4", "box-seam-fill", "truck", "bar-chart-line-fill", "people-fill"],
        orientation="horizontal",
        styles={
            "container": {"padding": "0!important", "background-color": "#fafafa", "border-radius": "10px"},
            "icon": {"color": "#4F4F4F", "font-size": "20px"},
            "nav-link": {"font-size": "16px", "text-align": "center", "margin":"0px", "--hover-color": "#E0E0E0", "color": "#333333"},
            "nav-link-selected": {"background-color": "#27AE60", "color": "white", "font-weight": "bold"},
        }
    )

    if selected == "Dashboard":
        st.title("📈 Dashboard de Performance")
        
        df_produtos, df_movimentacoes = get_dashboard_data(supabase)

        if df_produtos.empty:
            st.warning("Ainda não há dados suficientes para exibir o dashboard.")
            return

        # --- KPIs (Indicadores Chave de Performance) ---
        st.subheader("Indicadores Chave")
        
        df_produtos['data_validade'] = pd.to_datetime(df_produtos['data_validade'], errors='coerce')
        
        brasilia_tz = pytz.timezone("America/Sao_Paulo")
        hoje = datetime.now(brasilia_tz).date()

        valor_estoque = (df_produtos['estoque_atual'] * df_produtos['preco_venda']).sum()
        itens_baixo_estoque = df_produtos[df_produtos['estoque_atual'] <= df_produtos['qtd_minima_estoque']].shape[0]
        
        df_com_validade = df_produtos[df_produtos['data_validade'].notna()]
        itens_vencendo = df_com_validade[
            (df_com_validade['data_validade'].dt.date >= hoje) &
            (df_com_validade['data_validade'].dt.date <= hoje + timedelta(days=30))
        ].shape[0]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Valor de Venda do Estoque", f"R$ {valor_estoque:,.2f}")
        col2.metric("Itens com Estoque Baixo", f"{itens_baixo_estoque}")
        col3.metric("Itens Vencendo em 30 dias", f"{itens_vencendo}", help="Produtos que irão vencer nos próximos 30 dias.")

        st.divider()

        # --- Gráficos ---
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Top 5 Produtos com Mais Estoque")
            if not df_produtos.empty:
                top_estoque = df_produtos.nlargest(5, 'estoque_atual')
                st.bar_chart(top_estoque.set_index('nome')['estoque_atual'])

        with c2:
            st.subheader("Produtos Próximos do Vencimento")
            if not df_com_validade.empty:
                df_vencendo = df_com_validade.copy()
                df_vencendo['dias_para_vencer'] = (df_vencendo['data_validade'].dt.date - hoje).dt.days
                df_vencendo_proximo = df_vencendo[df_vencendo['dias_para_vencer'] >= 0].nsmallest(5, 'dias_para_vencer')
                
                if not df_vencendo_proximo.empty:
                    st.dataframe(
                        df_vencendo_proximo[['nome', 'dias_para_vencer']].rename(columns={'nome': 'Produto', 'dias_para_vencer': 'Dias para Vencer'}),
                        hide_index=True, use_container_width=True
                    )
                else:
                    st.info("Nenhum produto a vencer nos próximos dias.")
            else:
                st.info("Nenhum produto com data de validade cadastrada.")

    elif selected == "PDV":
        pdv_page.render_page(supabase)
    elif selected == "Produtos":
        gestao_produtos_page.render_page(supabase)
    elif selected == "Movimentação":
        movimentacao_page.render_page(supabase)
    elif selected == "Relatórios":
        if st.session_state.user_role == 'Admin':
            relatorios_page.render_page(supabase)
        else:
            st.error("🚫 Acesso restrito a Administradores.")
    elif selected == "Usuários":
        if st.session_state.user_role == 'Admin':
            gerenciamento_usuarios_page.render_page(supabase)
        else:
            st.error("🚫 Acesso restrito a Administradores.")

if __name__ == "__main__":
    main()
