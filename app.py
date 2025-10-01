import time
from datetime import datetime, timezone
from io import BytesIO
from unicodedata import normalize

import streamlit as st
from dotenv import load_dotenv

from core.crud import (find_enrollment_by_token_and_semester,
                       find_student_by_matricula, get_configuracoes,
                       get_turmas, save_enrollment)
from core.database import get_database, get_db_connection
from utils.enem import (extract_hash_from_pdf, fetch_enem_scores,
                        parse_relevant_scores)
from utils.generate_pdf import generate_pdf
from utils.style import load_css, load_image_as_base64


def display_status_page(title: str, message: str, date: datetime):
    """Função genérica para exibir página de status."""
    st.title(title)
    formatted_date = date.strftime('%d/%m/%Y às %H:%M')
    st.markdown(f"### {message.replace('{date}', formatted_date)}")
    st.markdown('---')
    st.markdown(
        'Para mais informações, acesse o [site do departamento](https://www.cchla.ufpb.br/dlpl/).'
    )
    st.stop()


def verify_names_match(name1: str, name2: str) -> bool:
    def normalize_name(name: str) -> str:
        name = (
            normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')
        )
        return ''.join(name.lower().split())

    return normalize_name(name1) == normalize_name(name2)


def initialize_session_state():
    if 'step' not in st.session_state:
        st.session_state.step = 'identificacao'
        st.session_state.matricula = ''
        st.session_state.aluno_data = None
        st.session_state.enem_data = None
        st.session_state.existing_enrollment = None
        st.session_state.is_update = False
        st.session_state.info_message = ''


def display_logo():
    logo_base64 = load_image_as_base64('logo.png')
    if logo_base64:
        st.markdown(
            f'<div class="logo-container"><img src="data:image/png;base64,{logo_base64}" class="logo-img"></div>',
            unsafe_allow_html=True,
        )


def handle_identificacao_step(db):
    st.title('Sistema de Inscrição')
    with st.form(key='form_matricula'):
        st.header('Passo 1: Identificação')
        matricula_input = st.text_input(
            'Digite sua Matrícula do SIGAA',
            value=st.session_state.get('matricula', ''),
            placeholder='Ex: 20240012345',
        ).strip()
        with st.expander('Alteração de Inscrição'):
            st.info(
                'Caso já tenha se inscrito, você pode usar este mesmo fluxo para **alterar sua turma ou opção de escolha** a qualquer momento antes do fim do período de inscrições, basta inserir sua matrícula e pdf(ou token) do ENEM novamente.'
            )
        submit_button = st.form_submit_button(
            label='Verificar Matrícula', use_container_width=True
        )
    if submit_button:
        if not matricula_input:
            st.error('Por favor, informe sua matrícula.')
            return
        with st.spinner('Verificando matrícula...'):
            aluno = find_student_by_matricula(db, matricula_input)
            st.session_state.matricula = matricula_input
            if aluno:
                st.session_state.aluno_data = aluno
                st.session_state.is_calouro = False
                st.session_state.step = 'validacao_enem'
                st.rerun()
            else:
                ano_atual = str(datetime.now().year)
                if (
                    matricula_input.startswith(ano_atual)
                    and matricula_input.isdigit()
                ):
                    st.session_state.aluno_data = {
                        'Matricula': matricula_input
                    }
                    st.session_state.is_calouro = True
                    st.session_state.info_message = 'Matrícula não encontrada. Identificamos que você é um provável calouro. Vamos confirmar seus dados com o ENEM.'
                    st.session_state.step = 'validacao_enem'
                    st.rerun()
                else:
                    st.error(
                        'Matrícula não encontrada. Verifique se digitou corretamente e tente novamente.'
                    )


def handle_validacao_enem_step(db, config):
    if st.session_state.info_message:
        st.info(st.session_state.info_message)
        st.session_state.info_message = ''
    aluno_nome = st.session_state.aluno_data.get('Nome', 'Aluno(a)').split()[0]
    st.title(
        f'Olá, {aluno_nome}!'
        if not st.session_state.is_calouro
        else 'Bem-vindo(a)!'
    )
    st.header('Passo 2: Resultado do ENEM')
    st.warning(
        'Seu token do ENEM é pessoal e permite o acesso às suas notas. **Não o compartilhe.**'
    )
    tab1, tab2 = st.tabs(['Anexar PDF', 'Inserir Token Manualmente'])
    hash_token = None
    with tab1:
        st.subheader('Opção 1: Anexar o PDF do ENEM')
        with st.expander('Clique para ver as instruções'):
            st.markdown(
                '1. Acesse a [Página do Participante do ENEM](https://enem.inep.gov.br/participante/) e faça login com o gov.br.\n\n2. Clique em "Edições Anteriores" e selecione o ano mais recente que você participou.\n\n3. Clique em "Versão impressa" e depois em "Imprimir" para baixar o PDF com suas notas.\n\n4. Anexe o PDF abaixo.'
            )
        enem_pdf = st.file_uploader(
            'Anexe o PDF oficial do ENEM aqui', type='pdf', key='pdf_uploader'
        )
        if enem_pdf:
            with st.spinner('Analisando o PDF...'):
                hash_token = extract_hash_from_pdf(BytesIO(enem_pdf.read()))
                if hash_token:
                    st.success('Token extraído com sucesso do PDF!')
                else:
                    st.error('Token não encontrado no PDF.')
    with tab2:
        st.subheader('Opção 2: Inserir o Token Manualmente')
        with st.expander('Clique para ver as instruções'):
            st.markdown(
                '1. Abra o [PDF oficial do ENEM](https://enem.inep.gov.br/participante/) que você baixou.\n\n2. Procure por "Chave de validação" no documento.\n\n3. Copie o código alfanumérico completo (incluindo sinais de igual no final, se houver).\n\n4. Cole o token no campo abaixo.'
            )
        manual_token_input = st.text_input(
            'Cole o Token de Validação aqui:',
            key='manual_token_input',
            placeholder='Ex: zDdMdIblbpDr/DxLOPgr6w==',
        ).strip()
        if manual_token_input:
            hash_token = manual_token_input
    if st.button(
        'Verificar Notas do ENEM', type='primary', use_container_width=True
    ):
        if not hash_token:
            st.warning(
                'Por favor, anexe um PDF válido ou insira o token para continuar.'
            )
            return
        with st.spinner(
            'Consultando a API do INEP e verificando inscrição...'
        ):
            enem_data = fetch_enem_scores(hash_token)
            if not enem_data:
                st.error(
                    'Falha ao validar suas notas. O serviço do INEP pode estar instável ou o token é inválido.'
                )
                return
            existing_enrollment = find_enrollment_by_token_and_semester(
                db, enem_data.get('hash'), config.get('activeSemester', 'N/A')
            )
            if existing_enrollment:
                st.session_state.is_update = True
                st.session_state.existing_enrollment = existing_enrollment
                st.session_state.info_message = 'Encontramos sua inscrição anterior. Você pode revisar e alterar suas escolhas abaixo.'
            nome_sigaa = st.session_state.aluno_data.get('Nome')
            nome_enem = enem_data.get('nome', '')
            if st.session_state.is_calouro:
                st.session_state.aluno_data['Nome'] = nome_enem
                st.session_state.aluno_data['Curso'] = 'A ser confirmado'
            elif not verify_names_match(nome_sigaa, nome_enem):
                st.error(
                    f"O nome no ENEM ('{nome_enem}') não corresponde ao da matrícula ('{nome_sigaa}'). Verifique o pdf/token inserido e tente novamente."
                )
                return
            st.session_state.enem_data = enem_data
            st.session_state.step = 'confirmacao'
            st.success('Notas validadas com sucesso!')
            time.sleep(1.5)
            st.rerun()


def handle_confirmacao_step(db, config):
    st.title('Finalize sua Inscrição')
    if st.session_state.info_message:
        st.info(st.session_state.info_message)
        st.session_state.info_message = ''
    with st.form('form_final'):
        st.header('Passo 3: Escolha e Confirmação')
        aluno_info = st.session_state.aluno_data
        enem_info = st.session_state.enem_data
        relevant_scores = parse_relevant_scores(enem_info) if enem_info else {}
        st.write(f"**Nome:** {aluno_info.get('Nome', 'N/A')}")
        st.write(f"**Matrícula:** {aluno_info.get('Matricula', 'N/A')}")
        st.write(f"**Curso:** {aluno_info.get('Curso', 'A ser confirmado')}")
        st.write(f"**Semestre:** {config.get('activeSemester', 'N/A')}")
        if relevant_scores:
            st.success(
                f"**Nota para Classificação:** {relevant_scores.get('nota_predita', 'N/A')}"
            )
            st.caption(
                f"Baseada na Redação ({relevant_scores.get('nota_redacao', 'N/A')}) e Linguagens ({relevant_scores.get('nota_linguagens', 'N/A')})."
            )
        turmas_disponiveis = get_turmas(
            db, config.get('activeSemester', 'N/A')
        )
        if not turmas_disponiveis:
            turmas_disponiveis = ['Turmas não disponíveis']
        previous_turma = (
            st.session_state.existing_enrollment.get('turma_escolhida')
            if st.session_state.existing_enrollment
            else turmas_disponiveis[0]
        )
        turma_selecionada = st.selectbox(
            'Selecione a turma desejada',
            turmas_disponiveis,
            index=turmas_disponiveis.index(previous_turma)
            if previous_turma in turmas_disponiveis
            else 0,
        )
        escolha_options = ['Cursar disciplina', 'Dispensa de disciplina']
        nota_minima_dispensa = config.get('cutoffScore', 6.75)
        if relevant_scores.get('nota_predita', 0) < nota_minima_dispensa:
            escolha_options = [escolha_options[0]]
            st.info(
                f"Sua nota é inferior a {nota_minima_dispensa}, portanto apenas a opção 'Cursar disciplina' está disponível."
            )
        previous_escolha = (
            st.session_state.existing_enrollment.get('escolha')
            if st.session_state.existing_enrollment
            else escolha_options[0]
        )
        escolha_selecionada = st.selectbox(
            'Você deseja:',
            escolha_options,
            index=escolha_options.index(previous_escolha)
            if previous_escolha in escolha_options
            else 0,
        )
        button_label = (
            'Atualizar Inscrição'
            if st.session_state.is_update
            else 'Confirmar Inscrição'
        )
        submit_button = st.form_submit_button(
            button_label, use_container_width=True
        )
    if submit_button:
        with st.spinner('Salvando sua inscrição...'):
            try:
                final_enrollment_data = {
                    **aluno_info,
                    'turma_escolhida': turma_selecionada,
                    'token_enem': enem_info.get('hash'),
                    'notas_relevantes': relevant_scores,
                    'escolha': escolha_selecionada,
                    'semester': config.get('activeSemester', 'N/A'),
                }
                save_enrollment(db, final_enrollment_data)
                st.session_state.final_data = {
                    **final_enrollment_data,
                    'is_update': st.session_state.is_update,
                    'data_ultima_atualizacao': datetime.now().isoformat(),
                }
                st.session_state.step = 'finalizado'
                st.rerun()
            except Exception as e:
                st.error(
                    f'Ocorreu um erro interno ao salvar. Tente novamente. Erro: {e}'
                )


def handle_finalizado_step():
    st.balloons()
    st.title('Inscrição Realizada com Sucesso!')
    st.success(
        'Sua inscrição foi confirmada e registrada. Salve seu comprovante abaixo.'
    )
    pdf_buffer = generate_pdf(st.session_state.final_data)
    st.download_button(
        label='Baixar Comprovante de Inscrição em PDF',
        data=pdf_buffer,
        file_name=f"comprovante_{st.session_state.final_data.get('Matricula', 'aluno')}.pdf",
        mime='application/pdf',
        use_container_width=True,
        type='primary',
    )
    if st.button(
        'Realizar Nova Inscrição ou Alterar Dados', use_container_width=True
    ):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


def main():
    st.set_page_config(
        page_title='Inscrição | DLPL', page_icon='📝', layout='centered'
    )
    load_dotenv()
    load_css()
    client = get_db_connection()
    db = get_database(client)

    display_logo()

    if db is None:
        st.error(
            'Falha na conexão com o banco de dados. O sistema está indisponível.'
        )
        st.stop()

    config = get_configuracoes(db)
    if not config:
        st.error(
            'Não foi possível carregar as configurações do sistema. Tente novamente mais tarde.'
        )
        st.stop()

    now = datetime.now(timezone.utc)
    start_date = config.get('enrollmentStartDate')
    end_date = config.get('enrollmentEndDate')

    if not start_date or not end_date:
        st.error(
            'As datas de inscrição não estão configuradas corretamente no sistema.'
        )
        st.stop()

    if isinstance(start_date, datetime) and start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)
    if isinstance(end_date, datetime) and end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)

    if now < start_date:
        display_status_page(
            title='Inscrições em Breve',
            message='O período de inscrições ainda não começou. As inscrições abrirão em {date}.',
            date=start_date,
        )

    if now > end_date:
        display_status_page(
            title='Inscrições Encerradas',
            message='O período de inscrições foi finalizado em {date}.',
            date=end_date,
        )

    initialize_session_state()

    steps = {
        'identificacao': lambda: handle_identificacao_step(db),
        'validacao_enem': lambda: handle_validacao_enem_step(db, config),
        'confirmacao': lambda: handle_confirmacao_step(db, config),
        'finalizado': handle_finalizado_step,
    }
    step_function = steps.get(st.session_state.step)
    if step_function:
        step_function()


if __name__ == '__main__':
    main()
