import streamlit as st
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.server_api import ServerApi


@st.cache_resource
def get_db_connection() -> MongoClient:
    """Estabelece e retorna uma conexão com o cliente MongoDB."""
    try:
        uri = st.secrets['MONGO_URI']
        client = MongoClient(uri, server_api=ServerApi('1'))
        client.admin.command('ping')
        return client
    except Exception as e:
        st.error(f'Erro ao conectar com o MongoDB: {e}')
        return None


def get_database(client: MongoClient) -> Database:
    """Retorna uma instância do banco de dados a partir de um cliente conectado."""
    if client:
        return client['DLPL']
    return None
