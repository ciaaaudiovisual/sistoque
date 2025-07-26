import streamlit as st
from supabase import create_client
import pandas as pd

# --- Conexão ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- Verificação de Permissão ---
if 'user_role' not in st.session_state or st.session_state.user_role != 'Admin':
    st.error("🚫 Acesso negado. Você precisa ser um Administrador para acessar esta página.")
    st.stop() # Interrompe a execução da página

# --- Layout e Funções da Página ---
st.title("👑 Gerenciamento de Usuários e Permissões")

# Função para buscar todos os perfis
def get_all_profiles():
    response = supabase.table('perfis').select('*').execute()
    return pd.DataFrame(response.data)

tab1, tab2 = st.tabs(["Convidar Novo Usuário", "Gerenciar Usuários Existentes"])

with tab1:
    st.subheader("Convidar Novo Usuário")
    with st.form("invite_form", clear_on_submit=True):
        email = st.text_input("Email do novo usuário")
        cargo = st.selectbox("Selecione o Cargo", ["Operador", "Admin"])
        
        submitted = st.form_submit_button("Enviar Convite")
        if submitted:
            try:
                # O Supabase Auth lida com o envio do convite por email
                # A senha será definida pelo próprio usuário no primeiro acesso
                # Precisamos usar a SERVICE_ROLE_KEY para convidar usuários
                # Guarde-a nos seus secrets como SUPABASE_SERVICE_KEY
                
                # ATENÇÃO: A função invite_user_by_email foi descontinuada em algumas bibliotecas.
                # A forma moderna é criar o usuário e ele receberá um email de confirmação/convite.
                
                # Usando a chave de serviço para ter privilégios de admin
                supabase_admin = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_KEY"])
                
                # Cria o usuário
                new_user = supabase_admin.auth.admin.create_user({
                    "email": email,
                    "email_confirm": True, # O usuário precisará confirmar o email
                })
                
                # Atualiza o cargo do usuário recém-criado na tabela perfis
                user_id = new_user.user.id
                supabase.table('perfis').update({'cargo': cargo}).eq('id', user_id).execute()

                st.success(f"Convite enviado para {email} com o cargo de {cargo}!")
            except Exception as e:
                st.error(f"Erro ao convidar usuário: {e}")

with tab2:
    st.subheader("Usuários Cadastrados")
    df_perfis = get_all_profiles()
    
    if not df_perfis.empty:
        # st.data_editor é ideal para isso
        df_editado = st.data_editor(
            df_perfis,
            column_config={
                "id": None, # Oculta ID
                "cargo": st.column_config.SelectboxColumn(
                    "Cargo",
                    options=["Admin", "Operador"],
                    required=True,
                )
            },
            hide_index=True,
            use_container_width=True
        )
        
        if st.button("Salvar Alterações de Cargo"):
            # Lógica para atualizar os cargos que foram alterados
            for index, row in df_editado.iterrows():
                original_row = df_perfis.iloc[index]
                if row['cargo'] != original_row['cargo']:
                    user_id = row['id']
                    novo_cargo = row['cargo']
                    supabase.table('perfis').update({'cargo': novo_cargo}).eq('id', user_id).execute()
            
            st.success("Cargos atualizados com sucesso!")
            st.rerun()

    else:
        st.info("Nenhum perfil encontrado.")
