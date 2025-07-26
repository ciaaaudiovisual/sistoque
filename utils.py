import streamlit as st
from supabase import create_client, Client # Importar o tipo Client

@st.cache_resource
def init_connection():
    """Inicializa e retorna o cliente de conexão com o Supabase."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except KeyError:
        st.error("ERRO: As credenciais 'SUPABASE_URL' e 'SUPABASE_KEY' não foram encontradas nos Secrets do Streamlit.")
        st.info("Por favor, adicione as credenciais ao arquivo secrets.toml e reinicie o app.")
        return None
    except Exception as e:
        st.error(f"Erro ao conectar com o Supabase. Verifique suas credenciais. Detalhes: {e}")
        return None

# Função hash para o cliente Supabase, para que o @st.cache_data funcione
# Isso diz ao Streamlit para identificar o cliente por seu ID de objeto na memória, em vez de seu conteúdo.
def supabase_client_hash_func(client: Client) -> int:
    return id(client)
