CREATE TABLE cadastro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    cpf TEXT NOT NULL UNIQUE,
    data_nascimento TEXT NOT NULL,
    genero TEXT NOT NULL,
    endereco TEXT NOT NULL,
    telefone TEXT NOT NULL,
    pressao_arterial TEXT,
    altura REAL,
    peso REAL,
    frequencia_atividades_sem INTEGER,
    sono_regular TEXT,
    dieta_planejada TEXT,
    historico_doencas TEXT,
    data_registro TEXT NOT NULL
);