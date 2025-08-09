import streamlit as st
from streamlit_option_menu import option_menu
from streamlit_js_eval import streamlit_js_eval
import re
import pandas as pd
from datetime import datetime, timedelta
import pytz

# Importações de outros ficheiros do seu projeto
from utils import init_connection
from pages import gestao_produtos_page, gerenciamento_usuarios_page, movimentacao_page, pdv_page, relatorios_page

st.set_page_config(page_title="Sistoque | Sistema de Gestão", layout="wide")

# Inicializa o cliente Supabase
supabase = init_connection()

if not supabase:
    st.error("Falha fatal na conexão com o banco de dados. Verifique os Secrets.")
    st.stop()

# --- Gerenciamento de Estado da Sessão ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
# --- NOVA FLAG PARA CONTROLE DE RECARGA ---
if 'recovery_attempt' not in st.session_state:
    st.session_state.recovery_attempt = False

# --- Funções de Autenticação ---
def get_user_profile(user_id):
    response = supabase.table('perfis').select('cargo, status, nome_completo').eq('id', user_id).single().execute()
    return response.data if response.data else None

def logout():
    st.session_state.user = None
    st.session_state.user_role = None
    st.session_state.recovery_attempt = False # Limpa a flag no logout
    st.cache_data.clear()
    streamlit_js_eval(js_expressions='window.location.hash = ""')
    st.rerun()

# --- TELA DE LOGIN / RECUPERAÇÃO DE SENHA ---
if st.session_state.user is None:
    st.markdown("""<style>[data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)
    
    url_hash = streamlit_js_eval(js_expressions='window.location.hash', want_output=True)
    
    params = {}
    if url_hash and isinstance(url_hash, str) and url_hash.startswith('#'):
        st.session_state.recovery_attempt = True # Ativa a flag se encontrarmos um hash
        param_list = url_hash[1:].split('&')
        for param in param_list:
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = value

    access_token = params.get("access_token")
    
    # --- LÓGICA ATUALIZADA PARA LIDAR COM TIMING ---
    # Se o tipo na URL for recovery mas o token ainda não foi lido (primeira carga)
    if url_hash and "type=recovery" in url_hash and not access_token and not st.session_state.get('recovery_processed', False):
        st.session_state.recovery_processed = True
        st.rerun() # Força a recarga para dar tempo ao JS de pegar o hash

    elif params.get("type") == "recovery" and access_token:
        st.title("🔑 Defina sua Nova Senha")
        with st.form("update_password_form"):
            new_password = st.text_input("Nova Senha", type="password")
            confirm_password = st.text_input("Confirme a Nova Senha", type="password")
            
            if st.form_submit_button("Atualizar Senha", type="primary"):
                if not new_password or new_password != confirm_password:
                    st.error("As senhas não correspondem ou estão em branco.")
                else:
                    try:
                        supabase.auth.update_user({"password": new_password}, access_token=access_token)
                        st.success("Sua senha foi atualizada com sucesso! Você já pode fazer o login.")
                        st.balloons()
                        st.session_state.recovery_processed = False # Reseta a flag
                        streamlit_js_eval(js_expressions='window.location.hash = ""')
                    except Exception as e:
                        st.error(f"Não foi possível atualizar a senha. O link pode ter expirado. Erro: {e}")
    else:
        # Reseta a flag se sairmos do fluxo de recuperação
        st.session_state.recovery_processed = False
        st.title("📦 Sistoque | Controle de Estoque e Vendas")
        login_tab, signup_tab = st.tabs(["Entrar", "Cadastre-se"])
        
        with login_tab:
            # ... (código do formulário de login e do expander "esqueci minha senha" permanece o mesmo) ...
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar"):
                    try:
                        session = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        profile = get_user_profile(session.user.id)
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
                            supabase.auth.reset_password_for_email(email_reset)
                            st.success("Se este e-mail estiver cadastrado, um link para redefinir sua senha foi enviado.")
                        except Exception as e:
                            st.error(f"Ocorreu um erro: {e}")
        
        with signup_tab:
            # ... (código do formulário de cadastro permanece o mesmo) ...
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

# --- APLICAÇÃO PRINCIPAL PÓS-LOGIN ---
else:
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
        styles={
            "container": {"padding": "0!important", "background-color": "#fafafa", "border-radius": "10px"},
            "icon": {"color": "#4F4F4F", "font-size": "20px"},
            "nav-link": {"font-size": "16px", "text-align": "center", "margin":"0px", "--hover-color": "#E0E0E0", "color": "#333333"},
            "nav-link-selected": {"background-color": "#27AE60", "color": "white", "font-weight": "bold"},
        }
    )

    if selected == "Dashboard":
        st.title("📈 Dashboard de Performance")
        st.info("O conteúdo do Dashboard pode ser implementado aqui.")

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
