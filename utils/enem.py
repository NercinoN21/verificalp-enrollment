import json
import re
from io import BytesIO
from time import sleep
from typing import Any, Dict

import pypdf
import requests
import streamlit as st

ENEM_API_URL = st.secrets['ENEM_API_URL']


def extract_hash_from_pdf(pdf_file: BytesIO) -> str | None:
    try:
        reader = pypdf.PdfReader(pdf_file)
        full_text = ''
        for page in reader.pages:
            full_text += page.extract_text()
        match = re.search(r'([a-zA-Z0-9=/]+==)', full_text)
        if match:
            return match.group(1)
        return None
    except Exception:
        return None


def fetch_enem_scores(hash_token: str) -> Dict[str, Any] | None:
    """
    Busca os resultados do ENEM com retentativas e uma requisição que imita o cURL.
    """
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    payload = {'hash': hash_token}

    payload_str = json.dumps(payload)

    MAX_RETRIES = 5
    RETRY_DELAY_SECONDS = 1

    for _ in range(MAX_RETRIES):
        try:
            response = requests.post(
                ENEM_API_URL,
                headers=headers,
                data=payload_str,
                verify=False,
                timeout=15,
            )

            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            sleep(RETRY_DELAY_SECONDS)

    return None


def parse_relevant_scores(enem_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Extrai as notas de Redação e Linguagens do JSON de resposta do ENEM.
    """
    scores = {
        'nota_redacao': 'N/A',
        'nota_linguagens': 'N/A',
        'nota_predita': 'N/A',
    }

    try:
        scores['nota_redacao'] = enem_data.get('redacao', {}).get(
            'nota', 'N/A'
        )

        for prova in enem_data.get('provaObjetiva', []):
            if 'Linguagens' in prova.get('areaDeConhecimento', ''):
                scores['nota_linguagens'] = prova.get('nota', 'N/A')
                break

        scores['nota_predita'] = round(
            st.secrets['ENEM_PREDICTION_BASE']
            + st.secrets['ENEM_PREDICTION_LINGUAGENS']
            * float(
                scores['nota_linguagens'].replace(',', '.')
                if scores['nota_linguagens'] != 'N/A'
                else 0
            )
            + st.secrets['ENEM_PREDICTION_REDACAO']
            * float(
                scores['nota_redacao']
                if scores['nota_redacao'] != 'N/A'
                else 0
            ),
            2,
        )

    except Exception as e:
        print(f'Erro ao extrair notas: {e}')

    return scores
