import streamlit as st
import pandas as pd

@st.cache_data(ttl=60)
def get_all_profiles(supabase_client):
    response = supabase_client.rpc('get_all_user_profiles').execute()
    return pd.DataFrame(response.data)

def update_user_status(supabase_client, user_id, new_status):
    try:
        supabase_client.table('perfis').update({'status': new_status}).eq('id', user_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar status: {e}")
        return False

def render_page(supabase_client):
    st.title("👑 Gerenciamento de Usuários e Permissões")

    if st.button("Atualizar Lista de Usuários"):
        st.cache_data.clear()

    df_perfis = get_all_profiles(supabase_client)

    if df_perfis.empty:
        st.warning("Nenhum usuário encontrado.")
    else:
        st.subheader("Usuários Pendentes de Ativação")
        df_pendentes = df_perfis[df_perfis['status'] == 'Pendente']

        if not df_pendentes.empty:
            for index, row in df_pendentes.iterrows():
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1: st.write(f"**Nome:** {row['nome_completo']}")
                with col2: st.write(f"**Email:** {row['email']}")
                with col3:
                    if st.button("✅ Ativar", key=f"ativar_{row['id']}", use_container_width=True):
                        if update_user_status(supabase_client, row['id'], 'Ativo'):
                            st.success(f"Usuário {row['nome_completo']} ativado!")
                            st.cache_data.clear()
                            st.rerun()
        else:
            st.success("Nenhum usuário pendente de ativação.")

        st.divider()
        st.subheader("Gerenciar Usuários Existentes")
        df_gerenciamento = df_perfis.copy()
        
        if not df_gerenciamento.empty:
            df_editado = st.data_editor(
                df_gerenciamento,
                column_config={
                    "id": None, "email": "Email", "nome_completo": "Nome",
                    "cargo": st.column_config.SelectboxColumn("Cargo", options=["Admin", "Operador"], required=True),
                    "status": st.column_config.SelectboxColumn("Status", options=["Ativo", "Inativo", "Pendente"], required=True),
                },
                hide_index=True, use_container_width=True, key="editor_usuarios"
            )

            if st.button("Salvar Alterações de Usuários"):
                 with st.spinner("Salvando..."):
                    originais = df_gerenciamento.set_index('id').to_dict('index')
                    editados = df_editado.set_index('id').to_dict('index')
                    for user_id, user_data in editados.items():
                        if user_id in originais and user_data != originais[user_id]:
                             supabase_client.table('perfis').update({'cargo': user_data['cargo'], 'status': user_data['status']}).eq('id', user_id).execute()
                    st.success("Alterações salvas!")
                    st.cache_data.clear()
                    st.rerun()
