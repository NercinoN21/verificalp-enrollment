from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import streamlit as st


def generate_pdf(data: dict) -> BytesIO:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    primary_color = HexColor('#4A7729')
    text_color = HexColor('#333333')
    try:
        c.drawImage(
            'logo.png',
            x=inch,
            y=height - 2 * inch,
            width=1.5 * inch,
            height=1.5 * inch,
            preserveAspectRatio=True,
            mask='auto',
        )
    except:
        st.warning("Arquivo 'logo.png' não encontrado.")
    c.setFont('Helvetica-Bold', 20)
    c.setFillColor(primary_color)
    c.drawCentredString(
        width / 2, height - 1.5 * inch, 'Comprovante de Inscrição'
    )
    c.setStrokeColor(primary_color)
    c.setLineWidth(1)
    c.line(inch, height - 2.2 * inch, width - inch, height - 2.2 * inch)
    y_position = height - 3 * inch
    line_height = 0.3 * inch

    update_time_str = 'N/A'
    try:
        LOCAL_TZ = ZoneInfo("America/Recife")
    except Exception:
        from datetime import timedelta
        LOCAL_TZ = timezone(timedelta(hours=-3))

    update_time_iso = data.get('data_ultima_atualizacao')

    if update_time_iso:
        try:
            parsed_time = datetime.fromisoformat(update_time_iso)
            parsed_time = parsed_time.astimezone(LOCAL_TZ)
            update_time_str = parsed_time.strftime('%d/%m/%Y às %H:%M:%S')
        except ValueError:
            update_time_str = 'N/A (data inválida)'

    info = [
        ('Nome Completo:', data.get('Nome', 'N/A')),
        ('Matrícula:', data.get('Matricula', 'N/A')),
        ('Curso:', data.get('Curso', 'N/A')),
        ('Semestre:', data.get('semester', 'N/A')),
        ('Turma Escolhida:', data.get('turma_escolhida', 'N/A')),
        ('Opção Escolhida:', data.get('escolha', 'N/A')),
        (
            'Nota de Redação:',
            str(data.get('notas_relevantes', {}).get('nota_redacao', 'N/A')),
        ),
        (
            'Nota de Linguagens:',
            str(
                data.get('notas_relevantes', {}).get('nota_linguagens', 'N/A')
            ),
        ),
        (
            'Nota Predita:',
            str(data.get('notas_relevantes', {}).get('nota_predita', 'N/A')),
        ),
        ('Última Atualização:', update_time_str),
        ('Token do ENEM:', data.get('token_enem', 'N/A')),
    ]

    status = (
        'Inscrição Atualizada'
        if data.get('is_update')
        else 'Inscrição Realizada'
    )
    info.insert(0, ('Status:', status))

    c.setFont('Helvetica', 12)
    c.setFillColor(text_color)
    for label, value in info:
        c.setFont('Helvetica-Bold', 12)
        c.drawString(inch, y_position, label)
        c.setFont('Helvetica', 12)
        c.drawString(inch + 2 * inch, y_position, value)
        y_position -= line_height

    c.setFont('Helvetica-Oblique', 9)
    c.setFillColor(HexColor('#888888'))

    if update_time_str != 'N/A' and 'inválida' not in update_time_str:
        c.drawCentredString(
            width / 2,
            1.2 * inch,
            f'Última atualização realizada em: {update_time_str}',
        )

    c.drawCentredString(
        width / 2,
        1.2 * inch,
        f'Última atualização realizada em: {update_time_str}',
    )
    c.drawCentredString(
        width / 2,
        inch,
        'Este é um documento gerado automaticamente pelo sistema.',
    )
    c.save()
    buffer.seek(0)
    return buffer
