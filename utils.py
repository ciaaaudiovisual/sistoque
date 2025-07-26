import streamlit as st
from supabase import create_client

@st.cache_resource
def init_connection():
    """Inicializa e retorna o cliente de conexão com o Supabase."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao conectar com o Supabase. Verifique seus Secrets. Detalhes: {e}")
        return None
