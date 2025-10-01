from datetime import datetime
from typing import Any, Dict

from pymongo.database import Database


def find_student_by_matricula(
    db: Database, matricula: str
) -> Dict[str, Any] | None:
    """
    Busca um aluno na coleção 'cursos.ufpb' pela sua matrícula.
    """
    pipeline = [
        {'$unwind': '$alunos_ativos'},
        {'$match': {'alunos_ativos.Matrícula': matricula}},
        {
            '$project': {
                '_id': 0,
                'Nome': '$alunos_ativos.Aluno',
                'Matricula': '$alunos_ativos.Matrícula',
                'Curso': '$Nome',
                'Centro': '$Centro',
            }
        },
    ]
    result = list(db['cursos.ufpb'].aggregate(pipeline))
    if result:
        return result[0]
    return None


def find_enrollment_by_token_and_semester(
    db: Database, token: str, semester: str
) -> Dict[str, Any] | None:
    """
    Busca uma inscrição na coleção 'inscricoes' pelo token do ENEM.
    """
    return db['inscricoes'].find_one(
        {'token_enem': token, 'semester': semester}
    )


def get_configuracoes(db: Database) -> Dict[str, Any]:
    """Busca as configurações ativas do sistema na coleção 'config'.
    Config só terá um documento.
    """
    config = db['config'].find_one()
    return config if config else {}


def get_turmas(db: Database, semestre: str) -> list[str]:
    """Busca as turmas disponíveis para o semestre atual na coleção 'turmas'."""
    collection = db['turma']
    results = collection.find(
        {'semester': semestre, 'is_active': True}, {'_id': 0, 'name': 1}
    )
    return [doc['name'] for doc in results]


def save_enrollment(db: Database, enrollment_data: Dict[str, Any]):
    """
    Salva ou atualiza os dados de uma inscrição na coleção 'inscricoes'.
    Usa o token_enem como identificador. Ao atualizar, altera apenas os campos
    necessários, preservando os dados originais.
    """
    collection = db['inscricoes']
    filter_query = {
        'token_enem': enrollment_data['token_enem'],
        'semester': enrollment_data['semester'],
    }
    update_fields = {
        'turma_escolhida': enrollment_data['turma_escolhida'],
        'escolha': enrollment_data['escolha'],
        'data_ultima_atualizacao': datetime.now().isoformat(),
    }
    initial_insert_fields = {
        k: v for k, v in enrollment_data.items() if k not in update_fields
    }
    initial_insert_fields['data_inscricao'] = datetime.now().isoformat()

    update_query = {
        '$set': update_fields,
        '$setOnInsert': initial_insert_fields,
    }
    result = collection.update_one(filter_query, update_query, upsert=True)
    return result
