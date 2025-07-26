import streamlit as st
from supabase import create_client, Client

# --- Configuração e Conexão ---
st.set_page_config(page_title="Login - Controle de Estoque", layout="centered")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- Gerenciamento de Estado da Sessão ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = None

# --- Funções de Autenticação ---
def get_user_role(user_id):
    response = supabase.table('perfis').select('cargo').eq('id', user_id).single().execute()
    if response.data:
        return response.data['cargo']
    return None

def login(email, password):
    try:
        session = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = session.user
        st.session_state.user_role = get_user_role(session.user.id)
        st.rerun() # Recarrega a página para refletir o estado de login
    except Exception as e:
        st.error(f"Falha no login: Verifique seu e-mail e senha.")

def logout():
    st.session_state.user = None
    st.session_state.user_role = None
    st.rerun()

# --- Layout da Interface ---

# Se o usuário não estiver logado, mostra a tela de login
if st.session_state.user is None:
    st.title("🍹 Controle de Estoque de Bebidas")
    st.subheader("Por favor, faça o login para continuar")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")
        if submitted:
            login(email, password)

# Se o usuário estiver logado, mostra a interface principal
else:
    st.sidebar.subheader(f"Bem-vindo(a)!")
    st.sidebar.write(f"Cargo: **{st.session_state.user_role}**")
    if st.sidebar.button("Sair", use_container_width=True):
        logout()

    st.title("🏠 Dashboard Principal")
    st.write("Selecione uma opção no menu à esquerda para começar.")
    
    # Mensagem de boas-vindas baseada no cargo
    if st.session_state.user_role == 'Admin':
        st.info("Você está logado como Administrador e tem acesso a todas as funcionalidades, incluindo o gerenciamento de usuários.", icon="👑")
    else:
        st.info("Você está logado como Operador. Seu acesso é focado na movimentação e consulta de estoque.", icon="👤")
