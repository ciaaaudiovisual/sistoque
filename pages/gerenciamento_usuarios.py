import streamlit as st
from supabase import create_client
import pandas as pd

# --- Conexão e Verificação de Permissão de Admin ---
# (O código de conexão e verificação de 'Admin' permanece o mesmo)
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

if 'user_role' not in st.session_state or st.session_state.user_role != 'Admin':
    st.error("🚫 Acesso negado.")
    st.stop()

# --- Funções ---
def get_all_profiles():
    # Agora buscamos também o email da tabela de usuários do Supabase
    response = supabase.rpc('get_all_user_profiles').execute()
    return pd.DataFrame(response.data)

def update_user_status(user_id, new_status):
    try:
        supabase.table('perfis').update({'status': new_status}).eq('id', user_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar status: {e}")
        return False

# CRIE ESTA FUNÇÃO NO SEU SQL EDITOR DO SUPABASE
# CREATE OR REPLACE FUNCTION get_all_user_profiles()
# RETURNS TABLE(id uuid, email text, nome_completo text, cargo text, status text) AS $$
# BEGIN
#     RETURN QUERY
#     SELECT p.id, u.email, p.nome_completo, p.cargo, p.status
#     FROM public.perfis p
#     JOIN auth.users u ON p.id = u.id;
# END;
# $$ LANGUAGE plpgsql;

# --- Layout da Página ---
st.title("👑 Gerenciamento de Usuários e Permissões")
st.info("Nesta tela você pode ativar novos usuários e gerenciar os existentes.")

# Botão para recarregar os dados
if st.button("Atualizar Lista de Usuários"):
    st.cache_data.clear()

df_perfis = get_all_profiles()

if df_perfis.empty:
    st.warning("Nenhum usuário encontrado.")
else:
    # --- Seção de Usuários Pendentes ---
    st.subheader("Usuários Pendentes de Ativação")
    df_pendentes = df_perfis[df_perfis['status'] == 'Pendente']

    if not df_pendentes.empty:
        for index, row in df_pendentes.iterrows():
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.write(f"**Nome:** {row['nome_completo']}")
            with col2:
                st.write(f"**Email:** {row['email']}")
            with col3:
                if st.button("Ativar Usuário", key=f"ativar_{row['id']}", use_container_width=True):
                    if update_user_status(row['id'], 'Ativo'):
                        st.success(f"Usuário {row['nome_completo']} ativado!")
                        st.rerun()
    else:
        st.success("Nenhum usuário pendente de ativação.")

    # --- Seção de Usuários Ativos e Inativos ---
    st.subheader("Gerenciar Usuários Ativos / Inativos")
    df_gerenciamento = df_perfis[df_perfis['status'] != 'Pendente']
    
    if not df_gerenciamento.empty:
        st.dataframe(df_gerenciamento, use_container_width=True, hide_index=True)
        # Aqui você pode adicionar lógica para alterar cargo ou desativar usuários
    else:
        st.info("Nenhum usuário ativo ou inativo para gerenciar.")
