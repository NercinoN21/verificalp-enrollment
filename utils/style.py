import base64
from pathlib import Path

import streamlit as st


def load_image_as_base64(image_path: str) -> str | None:
    """Carrega uma imagem local e a converte para base64 para embutir no app."""
    try:
        with Path(image_path).open('rb') as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        st.warning(f'Arquivo de imagem não encontrado em: {image_path}')
        return None


def load_css():
    """
    Carrega e injeta um CSS customizado que se adapta automaticamente
    aos temas claro e escuro do Streamlit.
    """
    st.markdown(
        """
    <style>
        /* Remove a barra superior do Streamlit */
        header {visibility: hidden;}

        /* --- TIPOGRAFIA --- */
        h1, h2, h3 { color: var(--text-color); }
        h1 { font-weight: 600; padding-bottom: 1rem; text-align: center; }
        h2 { font-weight: 600; text-align: center;}
        h3 { font-weight: 500; opacity: 0.8; padding-bottom: 1rem; text-align: center;}

        /* --- "CARDS" / CONTAINERS --- */
        div[data-testid="stForm"] {
            background-color: var(--secondary-background-color);
            border: 1px solid var(--border-color, rgba(128,128,128,0.2));
            border-radius: 18px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04);
            overflow: hidden;
            margin-bottom: 1.5rem;
        }
        div[data-testid="stForm"] > form {
            padding: 2rem 2.5rem;
        }

        /* --- WIDGETS (BOTÕES, INPUTS) --- */
        .stButton > button {
            border: none; border-radius: 12px; padding: 12px 24px;
            font-weight: 600; font-size: 15px; color: white;
            background-color: #4A7729; /* Verde do logo DLPL */
            transition: all 0.2s ease-in-out;
        }
        .stButton > button:hover {
            background-color: #3b6021;
            transform: translateY(-2px);
        }
        .stButton > button:focus {
            outline: none !important;
            box-shadow: 0 0 0 3px rgba(74, 119, 41, 0.4);
        }

        /* Inputs de texto e Selectbox */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
            border-radius: 12px !important;
            border: 1px solid var(--border-color, rgba(128,128,128,0.2)) !important;
            background-color: var(--background-color) !important;
            font-size: 16px !important;
        }
        .stTextInput input:focus, .stSelectbox > div > div:focus-within {
            border: 2px solid #4A7729 !important;
            box-shadow: 0 0 0 3px rgba(74, 119, 41, 0.4) !important;
        }

        /* --- LOGO --- */
        .logo-container {
            display: flex; justify-content: center;
            margin: 1rem 0 2rem 0;
        }
        .logo-img {
            max-width: 150px; height: 150px;
            filter: none !important; /* Impede que o tema escuro inverta as cores da logo */
        }
    </style>
    """,
        unsafe_allow_html=True,
    )
