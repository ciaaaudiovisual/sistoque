import streamlit as st
from streamlit_option_menu import option_menu
import re
from utils import init_connection
from pages import gestao_produtos_page, gerenciamento_usuarios_page, movimentacao_page, pdv_page, relatorios_page

st.set_page_config(page_title="Sistema de Estoque", layout="wide")

# Inicializa o cliente Supabase
supabase = init_connection()

# Se a conexão falhar, interrompe a execução
if not supabase:
    st.stop()

# --- Gerenciamento de Estado da Sessão ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = None

# --- Funções de Autenticação ---
def get_user_profile(user_id):
    response = supabase.table('perfis').select('cargo, status, nome_completo').eq('id', user_id).single().execute()
    return response.data if response.data else None

def logout():
    st.session_state.user = None
    st.session_state.user_role = None
    st.rerun()

# --- TELA DE LOGIN ---
if st.session_state.user is None:
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("📦 Sistema de Controle de Estoque e Vendas")
    
    login_tab, signup_tab = st.tabs(["Entrar", "Cadastre-se"])

    with login_tab:
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
                        st.error("Conta inativa ou não confirmada. Verifique seu e-mail (incluindo spam).")
                except Exception:
                    st.error("Falha no login. Verifique seu e-mail e senha.")

    with signup_tab:
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
                        new_user = supabase.auth.sign_up({
                            "email": email, "password": password,
                            "options": {"data": {'nome_completo': nome_completo}}
                        })
                        st.success("Cadastro realizado! Verifique seu e-mail para confirmação. Sua conta aguarda aprovação do administrador.")
                    except Exception as e:
                        st.error(f"Erro no cadastro: {e}")
else:
    # --- APLICATIVO PRINCIPAL PÓS-LOGIN ---
    
    with st.container():
        selected = option_menu(
            menu_title=None,
            options=["Dashboard", "PDV", "Produtos", "Movimentação", "Relatórios", "Usuários"],
            icons=["house", "cart4", "box-seam", "truck", "bar-chart-line", "people"],
            orientation="horizontal",
            # --- CORREÇÃO DE ESTILO APLICADA AQUI ---
            styles={
                "container": {"padding": "0!important", "background-color": "#fafafa", "border-radius": "10px"},
                "icon": {"color": "#4F4F4F", "font-size": "20px"},
                "nav-link": {
                    "font-size": "16px",
                    "text-align": "center",
                    "margin": "0px",
                    "--hover-color": "#E0E0E0",
                    "color": "#333333", # Cor do texto para itens não selecionados
                    "border-right": "1px solid #BDBDBD", # Borda para separar os itens
                },
                "nav-link-selected": {
                    "background-color": "#27AE60", # Verde um pouco diferente
                    "color": "white",
                    "font-weight": "bold",
                },
            }
        )
    
    st.sidebar.subheader(f"Bem-vindo(a), {st.session_state.user.user_metadata.get('nome_completo', '')}!")
    st.sidebar.write(f"Cargo: **{st.session_state.user_role}**")
    if st.sidebar.button("Sair (Logout)", use_container_width=True):
        logout()

    if selected == "Dashboard":
        st.title("📈 Dashboard Principal")
        st.write("Visão geral do seu negócio.")
        
    if selected == "PDV":
        pdv_page.render_page(supabase)
    
    if selected == "Produtos":
        gestao_produtos_page.render_page(supabase)

    if selected == "Movimentação":
        movimentacao_page.render_page(supabase)

    if selected == "Relatórios":
        if st.session_state.user_role == 'Admin':
            relatorios_page.render_page(supabase)
        else:
            st.error("🚫 Acesso restrito a Administradores.")
    
    if selected == "Usuários":
        if st.session_state.user_role == 'Admin':
            gerenciamento_usuarios_page.render_page(supabase)
        else:
            st.error("🚫 Acesso restrito a Administradores.")
