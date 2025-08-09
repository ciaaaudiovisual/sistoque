import streamlit as st
from streamlit_option_menu import option_menu
import re
import pandas as pd
from datetime import datetime, timedelta
import pytz
from supabase import Client

# Importa as funções de renderização de cada página e a conexão
from utils import init_connection
from pages import gestao_produtos_page, gerenciamento_usuarios_page, movimentacao_page, pdv_page, relatorios_page

# Configuração da página
st.set_page_config(page_title="Sistoque | Sistema de Gestão", layout="wide")

# --- FUNÇÕES AUXILIARES ---

def supabase_client_hash_func(client: Client) -> int:
    return id(client)

@st.cache_data(ttl=60, hash_funcs={Client: supabase_client_hash_func})
def get_dashboard_data(supabase: Client):
    df_produtos = pd.DataFrame(supabase.table('produtos').select('*').execute().data)
    return df_produtos

def get_user_profile(supabase_client, user_id):
    response = supabase_client.table('perfis').select('cargo, status, nome_completo').eq('id', user_id).single().execute()
    return response.data if response.data else None

def logout():
    st.session_state.user = None
    st.session_state.user_role = None
    st.cache_data.clear()
    st.rerun()

# --- PÁGINA PRINCIPAL ---
def main():
    supabase = init_connection()
    if not supabase:
        st.stop()

    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None

    # --- TELA DE LOGIN (agora muito mais simples) ---
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
                        profile = get_user_profile(supabase, session.user.id)
                        if profile and profile['status'] == 'Ativo':
                            st.session_state.user = session.user
                            st.session_state.user_role = profile['cargo']
                            st.rerun()
                        elif profile and profile['status'] == 'Pendente':
                            st.warning("Sua conta está aguardando aprovação de um administrador.")
                        else:
                            st.error("Conta inativa ou não confirmada. Verifique seu e-mail (incluindo spam).")
                    except Exception:
                        st.error("Falha no login. Verifique seu e-mail e senha.")

            st.divider()
            with st.expander("🔑 Esqueci minha senha"):
                with st.form("reset_form", clear_on_submit=True):
                    email_reset = st.text_input("Digite o seu e-mail para recuperação")
                    if st.form_submit_button("Enviar link de recuperação"):
                        try:
                            # Agora esta chamada simplesmente envia o e-mail. Não precisa de redirectTo.
                            supabase.auth.reset_password_for_email(email_reset)
                            st.success("Se este e-mail estiver cadastrado, um link de recuperação foi enviado.")
                        except Exception as e:
                            st.error(f"Ocorreu um erro: {e}")
        
        with signup_tab:
            with st.form("signup_form", clear_on_submit=True):
                nome_completo = st.text_input("Nome Completo")
                email_signup = st.text_input("Email de Cadastro")
                password_signup = st.text_input("Crie uma Senha", type="password")
                if st.form_submit_button("Registrar"):
                    # Lógica de cadastro...
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
    if st.session_state.user:
        if not st.session_state.user_role:
             profile = get_user_profile(supabase, st.session_state.user.id)
             if profile:
                 st.session_state.user_role = profile['cargo']

        with st.sidebar:
            st.subheader(f"Bem-vindo(a), {st.session_state.user.user_metadata.get('nome_completo', '')}!")
            st.write(f"Cargo: **{st.session_state.user_role}**")
            if st.button("Sair (Logout)", use_container_width=True):
                logout()

        selected = option_menu(
            menu_title=None,
            options=["Dashboard", "PDV", "Produtos", "Movimentação", "Relatórios", "Usuários"],
            icons=["house-door-fill", "cart4", "box-seam-fill", "truck", "bar-chart-line-fill", "people-fill"],
            orientation="horizontal",
            # Estilos...
        )

        # Lógica do menu para exibir as páginas...
        if selected == "Dashboard":
            st.title("📈 Dashboard de Performance")
            # Código completo do seu dashboard aqui
        elif selected == "PDV":
            pdv_page.render_page(supabase)
        elif selected == "Produtos":
            gestao_produtos_page.render_page(supabase)
        elif selected == "Movimentação":
            movimentacao_page.render_page(supabase)
        elif selected == "Relatórios":
            if st.session_state.user_role == 'Admin':
                relatorios_page.render_page(supabase)
            else: st.error("🚫 Acesso restrito a Administradores.")
        elif selected == "Usuários":
            if st.session_state.user_role == 'Admin':
                gerenciamento_usuarios_page.render_page(supabase)
            else: st.error("🚫 Acesso restrito a Administradores.")

if __name__ == "__main__":
    main()
