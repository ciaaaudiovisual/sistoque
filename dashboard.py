import streamlit as st
from supabase import create_client, Client
import re # Importa a biblioteca de expressões regulares para validar email

# --- Configuração e Conexão ---
st.set_page_config(page_title="Acesso - Controle de Estoque", layout="centered")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- Gerenciamento de Estado ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = None

# --- Funções ---
def get_user_profile(user_id):
    response = supabase.table('perfis').select('cargo, status').eq('id', user_id).single().execute()
    return response.data if response.data else None

def logout():
    st.session_state.user = None
    st.session_state.user_role = None
    st.rerun()

# --- Interface Principal ---
if st.session_state.user is None:
    st.title("🍹 Controle de Estoque de Bebidas")
    
    login_tab, signup_tab = st.tabs(["Entrar", "Cadastre-se"])

    with login_tab:
        st.subheader("Login")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar")
            if submitted:
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
                        st.error("Conta inativa ou não encontrada. Contate o suporte.")
                except Exception:
                    st.error("Falha no login. Verifique seu e-mail e senha.")

    with signup_tab:
        st.subheader("Criar Nova Conta")
        with st.form("signup_form", clear_on_submit=True):
            nome_completo = st.text_input("Nome Completo")
            email = st.text_input("Email de Cadastro")
            password = st.text_input("Crie uma Senha", type="password")
            
            submitted = st.form_submit_button("Registrar")
            if submitted:
                if not nome_completo or not email or not password:
                    st.error("Por favor, preencha todos os campos.")
                elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                     st.error("Formato de e-mail inválido.")
                else:
                    try:
                        # Cadastra o usuário no Supabase Auth
                        new_user = supabase.auth.sign_up({
                            "email": email,
                            "password": password,
                            "options": {
                                "data": {
                                    'nome_completo': nome_completo
                                }
                            }
                        })
                        st.success("Cadastro realizado! Sua conta está aguardando aprovação do administrador. Você receberá um email para confirmar sua conta.")
                    except Exception as e:
                        st.error(f"Erro no cadastro: {e}")
else:
    # --- Interface Pós-Login ---
    st.sidebar.subheader(f"Bem-vindo(a)!")
    st.sidebar.write(f"Cargo: **{st.session_state.user_role}**")
    if st.sidebar.button("Sair", use_container_width=True):
        logout()

    st.title("🏠 Dashboard Principal")
    st.write("Selecione uma opção no menu à esquerda para começar.")
