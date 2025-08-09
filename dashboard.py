import streamlit as st
from streamlit_option_menu import option_menu
import re
import pandas as pd
from datetime import datetime, timedelta
import pytz
import secrets # Para gerar códigos seguros
import smtplib # Para enviar e-mails
from email.mime.text import MIMEText
from supabase import create_client, Client

# Importações de outros ficheiros do seu projeto
from utils import init_connection
from pages import gestao_produtos_page, gerenciamento_usuarios_page, movimentacao_page, pdv_page, relatorios_page

st.set_page_config(page_title="Sistoque | Sistema de Gestão", layout="wide")

# --- FUNÇÕES ---

def get_user_profile(supabase_client, user_id):
    # ... (função existente)
    pass

def logout():
    # ... (função existente)
    pass

# --- NOVA FUNÇÃO PARA ENVIAR E-MAIL ---
def send_recovery_email(recipient_email, code):
    """Envia o e-mail de recuperação de senha."""
    try:
        # --- Configure com suas credenciais de e-mail ---
        sender_email = st.secrets["GMAIL_USER"]
        sender_password = st.secrets["GMAIL_APP_PASSWORD"]
        
        subject = f"Seu Código de Recuperação de Senha: {code}"
        body = f"""
        Olá,

        Você solicitou a recuperação de sua senha no Sistoque.

        Use o seguinte código para redefinir sua senha. Ele é válido por 10 minutos.

        Código: {code}

        Se você não solicitou isso, por favor ignore este e-mail.

        Atenciosamente,
        Equipe Sistoque
        """
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient_email

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(sender_email, sender_password)
            smtp_server.sendmail(sender_email, recipient_email, msg.as_string())
        
        return True, "E-mail enviado com sucesso!"
    except Exception as e:
        return False, f"Falha ao enviar e-mail: {e}"

# --- PÁGINA PRINCIPAL ---
def main():
    supabase = init_connection()
    if not supabase:
        st.stop()
    
    # ... (lógica de sessão existente)

    # --- TELA DE LOGIN ---
    if st.session_state.user is None:
        st.markdown("""<style>[data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)
        st.title("📦 Sistoque | Controle de Estoque e Vendas")
        
        login_tab, signup_tab = st.tabs(["Entrar", "Cadastre-se"])

        with login_tab:
          
            st.divider()
            with st.expander("🔑 Esqueci minha senha"):
                # Gerencia o fluxo de recuperação em etapas usando a sessão
                if 'reset_stage' not in st.session_state:
                    st.session_state.reset_stage = 'ask_email'

                if st.session_state.reset_stage == 'ask_email':
                    with st.form("request_code_form"):
                        email_reset = st.text_input("Digite seu e-mail para receber um código")
                        if st.form_submit_button("Enviar código"):
                            with st.spinner("Processando..."):
                                user_response = supabase.table('perfis').select('id').eq('email', email_reset).execute()
                                if user_response.data:
                                    user_id = user_response.data[0]['id']
                                    code = secrets.token_hex(3).upper() # Gera um código de 6 caracteres
                                    expires_at = (datetime.now(pytz.utc) + timedelta(minutes=10)).isoformat()
                                    
                                    # Salva o código e a validade no banco
                                    supabase.table('perfis').update({
                                        'reset_token': code,
                                        'reset_token_expires_at': expires_at
                                    }).eq('id', user_id).execute()

                                    # Envia o e-mail
                                    success, message = send_recovery_email(email_reset, code)
                                    if success:
                                        st.session_state.reset_stage = 'ask_code'
                                        st.session_state.reset_email = email_reset
                                        st.success("Código enviado! Verifique seu e-mail (e a pasta de spam).")
                                        st.rerun()
                                    else:
                                        st.error(message)
                                else:
                                    st.error("E-mail não encontrado no nosso sistema.")
                
                if st.session_state.reset_stage == 'ask_code':
                    with st.form("reset_password_form"):
                        st.info(f"Um código foi enviado para {st.session_state.reset_email}")
                        code_input = st.text_input("Código de Recuperação")
                        new_password = st.text_input("Nova Senha", type="password")
                        confirm_password = st.text_input("Confirme a Nova Senha", type="password")

                        if st.form_submit_button("Redefinir Senha"):
                             with st.spinner("Verificando..."):
                                # Conexão com privilégios de administrador
                                supabase_admin = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_KEY"])
                                
                                profile_response = supabase.table('perfis').select('*').eq('email', st.session_state.reset_email).single().execute()
                                profile = profile_response.data

                                if profile and profile['reset_token'] == code_input:
                                    expires_at = datetime.fromisoformat(profile['reset_token_expires_at'])
                                    if datetime.now(pytz.utc) > expires_at:
                                        st.error("Código expirado. Por favor, solicite um novo.")
                                    elif new_password != confirm_password or not new_password:
                                        st.error("As senhas não correspondem ou estão em branco.")
                                    else:
                                        # Atualiza a senha do usuário
                                        supabase_admin.auth.admin.update_user_by_id(profile['id'], {"password": new_password})
                                        # Limpa o token do banco
                                        supabase.table('perfis').update({'reset_token': None, 'reset_token_expires_at': None}).eq('id', profile['id']).execute()
                                        st.success("Senha atualizada com sucesso! Você já pode fazer o login.")
                                        del st.session_state.reset_stage
                                        del st.session_state.reset_email
                                        st.rerun()
                                else:
                                    st.error("Código inválido.")
            
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

if __name__ == "__main__":
    main()
