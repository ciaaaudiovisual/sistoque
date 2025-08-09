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

st.set_page_config(page_title="Sistoque | Sistema de Gestão", layout="wide")

# --- FUNÇÕES DE DADOS E CONEXÃO ---

# Esta função de hash é necessária se você passar o cliente supabase para uma função com cache
def supabase_client_hash_func(client: Client) -> int:
    """Função de hash para o cliente Supabase, para uso com cache."""
    return id(client)

@st.cache_data(ttl=60, hash_funcs={Client: supabase_client_hash_func})
def get_dashboard_data(supabase: Client):
    """Busca os dados necessários para o dashboard."""
    produtos_response = supabase.table('produtos').select('*').execute()
    # Adicionei um filtro de data para não carregar dados muito antigos desnecessariamente
    data_limite = (datetime.now() - timedelta(days=30)).isoformat()
    movimentacoes_response = supabase.table('movimentacoes').select('quantidade, produtos(preco_venda)').eq('tipo_movimentacao', 'SAÍDA').gte('data_movimentacao', data_limite).execute()
    
    df_produtos = pd.DataFrame(produtos_response.data)
    df_movimentacoes = pd.DataFrame(movimentacoes_response.data)
    
    return df_produtos, df_movimentacoes

def get_user_profile(supabase_client, user_id):
    """Busca o perfil do usuário no banco de dados."""
    response = supabase_client.table('perfis').select('cargo, status, nome_completo').eq('id', user_id).single().execute()
    return response.data if response.data else None

def logout():
    """Realiza o logout do usuário e limpa a sessão."""
    st.session_state.user = None
    st.session_state.user_role = None
    st.cache_data.clear()
    st.query_params.clear()
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

    # Tenta autenticar via token da URL (fluxo de recuperação de senha)
    params = st.query_params.to_dict()
    access_token = params.get("access_token")

    if access_token and not st.session_state.user:
        try:
            # Estabelece uma sessão temporária com o token
            session_response = supabase.auth.get_user(access_token)
            st.session_state.user = session_response.user
        except Exception:
            st.error("O link de recuperação de senha é inválido ou expirou. Por favor, solicite um novo.")
            access_token = None # Invalida o token se der erro
            st.query_params.clear()

    # --- LÓGICA DE EXIBIÇÃO ---

    # CASO 1: Usuário está logado (normalmente ou via link de recuperação)
    if st.session_state.user:
        # Se veio de um link de recuperação, mostra a tela para trocar a senha
        if access_token and params.get("type") == "recovery":
            st.title("🔑 Defina sua Nova Senha")
            with st.form("update_password_form"):
                new_password = st.text_input("Nova Senha", type="password")
                confirm_password = st.text_input("Confirme a Nova Senha", type="password")
                
                if st.form_submit_button("Atualizar Senha", type="primary"):
                    if not new_password or new_password != confirm_password:
                        st.error("As senhas não correspondem ou estão em branco.")
                    else:
                        try:
                            supabase.auth.update_user({"password": new_password})
                            st.success("Sua senha foi atualizada com sucesso!")
                            st.info("Você será desconectado para poder fazer login com sua nova senha.", icon="ℹ️")
                            st.balloons()
                            logout()
                        except Exception as e:
                            st.error(f"Não foi possível atualizar a senha. Erro: {e}")
        # Se está logado normalmente, mostra a aplicação
        else:
            if not st.session_state.user_role:
                profile = get_user_profile(supabase, st.session_state.user.id)
                if profile:
                    st.session_state.user_role = profile['cargo']

            with st.sidebar:
                st.subheader(f"Bem-vindo(a), {st.session_state.user.user_metadata.get('nome_completo', '')}!")
                st.write(f"Cargo: **{st.session_state.user_role}**")
                if st.button("Sair (Logout)", use_container_width=True):
                    logout()

            selected = option_menu(...) # Menu superior aqui
            # Lógica do menu aqui
            
    # CASO 2: Usuário não está logado e não está em fluxo de recuperação
    else:
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
                        # ... resto da lógica de login
                    except Exception:
                        st.error("Falha no login. Verifique seu e-mail e senha.")

            st.divider()
            with st.expander("🔑 Esqueci minha senha"):
                with st.form("reset_form", clear_on_submit=True):
                    email_reset = st.text_input("Digite o seu e-mail para recuperação")
                    if st.form_submit_button("Enviar link de recuperação"):
                        try:
                            # Passamos a URL do app para o Supabase saber para onde redirecionar
                            app_url = "https://sistoque.streamlit.app/" # CONFIRME SE ESTA É A URL CORRETA
                            supabase.auth.reset_password_for_email(
                                email_reset,
                                options={"redirect_to": app_url}
                            )
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
