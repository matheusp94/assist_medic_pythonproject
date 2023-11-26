import os
import sqlite3
from tabulate import tabulate
import logging
from datetime import datetime, timedelta
import unicodedata
from unidecode import unidecode
import re
from senha import API_KEY
import requests
import json


# Configurar o sistema de logging
logging.basicConfig(filename='app_log.txt', level=logging.INFO,
                    format='%(asctime)s [%(levelname)s]: %(message)s')


def conectar_bd():
    try:
        caminho_banco_dados = os.path.abspath(
            'database//atendimento_medico.db')
        conn = sqlite3.connect(caminho_banco_dados)
        cursor = conn.cursor()
        logging.info("Conexão com o banco de dados estabelecida.")
        return conn
    except sqlite3.Error as e:
        logging.error(f"Erro ao conectar ao banco de dados: {e}")
        print(f"Erro ao conectar ao banco de dados: {e}")
        exit(1)


def executar_setup(cursor):
    try:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cadastro'")
        tabela_existe = cursor.fetchone()

        if not tabela_existe:
            with open('setup.sql', 'r') as script:
                cursor.executescript(script.read())
            logging.info("Setup do banco de dados executado com sucesso.")
        else:
            logging.info(
                "A tabela cadastro já existe. Setup do banco de dados ignorado.")
    except sqlite3.Error as e:
        logging.error(f"Erro durante o setup do banco de dados: {e}")
        print(f"Erro durante o setup do banco de dados: {e}")
        exit(1)


###        VALIDAÇÕES         ###

def validar_genero(genero):
    return genero.upper() in ['M', 'F', 'N']


def validar_cpf(cpf):
    try:
        if not cpf.isdigit() or len(cpf) != 11:
            return False

        int_cpf = list(map(int, cpf))

        # Verificar se todos os dígitos são iguais, o que tornaria o CPF inválido
        if len(set(int_cpf)) == 1:
            return False

        # Primeiro dígito verificador
        total = 0
        for i in range(9):
            total += int_cpf[i] * (10 - i)
        resto = 11 - (total % 11)
        digito_verificador1 = 0 if resto > 9 else resto

        # Segundo dígito verificador
        total = 0
        for i in range(10):
            total += int_cpf[i] * (11 - i)
        resto = 11 - (total % 11)
        digito_verificador2 = 0 if resto > 9 else resto

        # Verificar se os dígitos verificadores são iguais aos fornecidos
        if digito_verificador1 == int_cpf[9] and digito_verificador2 == int_cpf[10]:
            return True
        else:
            return False
    except ValueError:
        return False


def validar_data(data_str):
    try:
        datetime.strptime(data_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validar_data_formato(data_str, formato="%Y-%m-%d"):
    try:
        datetime.strptime(data_str, formato)
        return True
    except ValueError:
        return False


def obter_data_valida(mensagem="Digite uma data (YYYY-MM-DD): "):
    while True:
        data_str = input(mensagem)
        if validar_data_formato(data_str):
            return data_str
        else:
            print("Formato de data inválido. Tente novamente.")


def remover_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


def validar_local(local):
    # Remover caracteres especiais e acentos usando unidecode
    local = unidecode(local)

    # Verifica se a string contém apenas letras e espaços
    return all(c.isalpha() or c.isspace() for c in local)


def validar_cep(cep):
    return cep.isdigit() and len(cep) == 8


def validar_telefone(telefone):
    # Expressão regular para validar o formato DDD9numero
    padrao_telefone = re.compile(r'^\d{2,3}9\d{8}$')
    return bool(re.match(padrao_telefone, telefone))


def validar_peso(peso):
    try:
        peso = float(peso)
        if peso <= 0:
            raise ValueError("O peso deve ser um valor positivo.")
        return True
    except ValueError:
        return False


def validar_altura(altura):
    try:
        altura = float(altura)
        if altura <= 0:
            raise ValueError("A altura deve ser um valor positivo.")
        return True
    except ValueError:
        return False


def obter_opcao(question, opcoes):  # utilizar quando a parte do questionario apresenta opções
    while True:
        print(f"\nOpções de {question}:")
        for i, opcao in enumerate(opcoes, start=1):
            print(f"{i}. {opcao}")

        opcao_escolhida = input(f"Escolha uma opção de {question}: ")

        if opcao_escolhida.isdigit() and 1 <= int(opcao_escolhida) <= len(opcoes):
            return opcoes[int(opcao_escolhida) - 1]
        else:
            print("Opção inválida. Tente novamente.")


def obter_opcao_sim_nao(pergunta):
    while True:
        opcao = input(f"{pergunta} (1 para sim, 2 para não): ").lower()
        if opcao in ['1', 'sim']:
            return 'sim'
        elif opcao in ['2', 'não', 'nao']:
            return 'não'
        else:
            print("Opção inválida. Por favor, escolha 1 para sim ou 2 para não.")


# em desuso abaixo
'''def obter_opcao_agendamento():
    while True:
        print("\nOpções de Agendamento:")
        print("1. Atendimento Imediato")
        print("2. Agendar")

        opcao = input("Escolha uma opção: ")

        if opcao == '1':
            return "Atendimento Imediato"
        elif opcao == '2':
            data_agendamento = input(
                "Digite a data do agendamento (DD-MM HH:mm): ")
            try:
                data_formatada = datetime.strptime(
                    f"{datetime.now().year}-{data_agendamento}:00", "%Y-%d-%m %H:%M:%S")
                if data_formatada < datetime.now():
                    print("A data inserida é anterior à data atual. Tente novamente.")
                else:
                    return data_formatada.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                print("Formato de data inválido. Tente novamente.")
        else:
            print("Opção inválida. Tente novamente.")'''


###         MAPEAMENTOS        ###


###         FUNÇÕES DE MENU          ###


def truncar_string(s, comprimento_maximo=20):
    """Trunca a string se exceder o comprimento máximo."""
    return (s[:comprimento_maximo - 3] + '...') if len(s) > comprimento_maximo else s


def exibir_resumo_registro(cursor, registro, comprimento_maximo_coluna=20):
    if registro:
        headers = [description[0] for description in cursor.description]
        values = list(registro)

        # Truncar valores das colunas que excedem o comprimento máximo
        values_truncados = [truncar_string(
            str(value), comprimento_maximo_coluna) for value in values]

        print("\nResumo do Registro:")
        print(tabulate([values_truncados], headers=headers, tablefmt="pretty"))

        return registro

    else:
        print("Registro não encontrado.")
        return None

def interagir_com_ia(registro):
    if registro:
        id_registro, nome_paciente, cpf, data_nascimento, genero, endereco, telefone, pressao_arterial, altura, peso, frequencia_atividades_sem, sono_regular, dieta_planejada, historico_doencas, data_registro = registro

        # Criar a string formatada para enviar para IA
        pergunta_formatada = f"""
        O paciente {nome_paciente}, nascido em {data_nascimento}, possui a pressão arterial de {pressao_arterial}.
        Sua altura é de {altura}m e seu peso de {peso}kg.
        O paciente pratica atividades físicas em uma frequência de {frequencia_atividades_sem}.
        Paciente possui um sono em torno de 7h/dia? {sono_regular}.
        Paciente possui dieta planejada? {dieta_planejada}.
        Segue um breve histórico de doenças do paciente: {historico_doencas}.
        Considerando suas informações, faça breves sugestões de cuidados médicos que são necessários previamente, antes do contato com um profissional da área.
        """

        print(pergunta_formatada)

        # Enviando pergunta para a IA
        headers = {"Authorization": f"Bearer {API_KEY}",
                   "Content-Type": "application/json"}
        link = "https://api.openai.com/v1/chat/completions"
        id_modelo = "gpt-3.5-turbo"

        body_mensagem = {
            "model": id_modelo,
            "messages": [{"role": "user", "content": pergunta_formatada}]
        }

        body_mensagem = json.dumps(body_mensagem)

        requisicao = requests.post(link, headers=headers, data=body_mensagem)

        # Verificando o status da resposta
        if requisicao.status_code == 200:
            resposta = requisicao.json()

            # Verificando a estrutura real do JSON retornado
            if "choices" in resposta:
                mensagem = resposta["choices"][0]["message"]["content"]
                print("Resposta da IA:", mensagem)
            else:
                print("Estrutura inesperada na resposta da API.")
        else:
            print(
                f"Falha na requisição. Código de status: {requisicao.status_code}")



def criar_registro(conn, cursor):
    try:
        print("(Digite 'x' a qualquer momento para voltar ao menu principal.)\n")

        nome_paciente = input("Nome do paciente: ")
        if nome_paciente.lower() == 'x':
            print("Operação cancelada. Voltando ao menu principal.")
            return
        while not nome_paciente.strip():
            print("Nome do paciente não pode ser deixado em branco.")
            nome_paciente = input("Nome do paciente: ")
            if nome_paciente.lower() == 'x':
                print("Operação cancelada. Voltando ao menu principal.")
                return

        cpf_input = input("CPF do paciente: ")
        if cpf_input.lower() == 'x':
            print("Operação cancelada. Voltando ao menu principal.")
            return
        while not validar_cpf(cpf_input):
            print(
                "CPF inválido. Por favor, entre com um CPF válido (11 dígitos numéricos) ou 'x' para cancelar.")
            cpf_input = input("CPF do paciente: ")
            if cpf_input.lower() == 'x':
                print("Operação cancelada. Voltando ao menu principal.")
                return

        data_nascimento_str = input("Data de Nascimento (YYYY-MM-DD): ")
        if data_nascimento_str.lower() == 'x':
            print("Operação cancelada. Voltando ao menu principal.")
            return
        while not validar_data(data_nascimento_str):
            print("Data de Nascimento inválida. Tente novamente ou 'x' para cancelar.")
            data_nascimento_str = input("Data de Nascimento (YYYY-MM-DD): ")
            if data_nascimento_str.lower() == 'x':
                print("Operação cancelada. Voltando ao menu principal.")
                return
        # Convertendo a string para um objeto datetime
        data_nascimento = datetime.strptime(data_nascimento_str, "%Y-%m-%d")

        genero = input(
            "Gênero (M para Masculino, F para Feminino, N para Não informar): ").upper()
        if genero == 'X':
            print("Operação cancelada. Voltando ao menu principal.")
            return
        while genero not in ['M', 'F', 'N']:
            print(
                "Opção inválida. Escolha M para Masculino, F para Feminino, ou N para Não informar.")
            genero = input(
                "Gênero (M para Masculino, F para Feminino, N para Não informar): ").upper()
            if genero == 'X':
                print("Operação cancelada. Voltando ao menu principal.")
                return

        endereco = input("Endereço paciente: ")
        # Verifica se o campo endereco não está em branco
        while not endereco.strip():
            print("O endereço não pode ser deixado em branco.")
            endereco = input("Endereço paciente: ")

        telefone = input("Telefone (no formato DDD9numero): ")
        if telefone.lower() == 'x':
            print("Operação cancelada. Voltando ao menu principal.")
            return
        while not validar_telefone(telefone):
            print("Telefone inválido. Tente novamente ou 'x' para cancelar.")
            telefone = input("Telefone (no formato DDD9numero): ")
            if telefone.lower() == 'x':
                print("Operação cancelada. Voltando ao menu principal.")
                return

        # obtendo presao arterial
        pressao_arterial_opcoes = [
            '12/8', '11/7.5', '13/8.5', '12.5/8.8', '14.5/9.5', '15/8.8',
            '16.5/10', '16/11', '19/13', '18/12', '8.5/5.5', '9/6', 'Não listado'
        ]
        pressao_arterial = obter_opcao(
            "Pressão Arterial mais próxima: ", pressao_arterial_opcoes)

        # altura e peso com validações
        altura_valida = False
        while not altura_valida:
            altura = input("Altura do paciente (em metros): ")
            if altura.lower() == 'x':
                print("Operação cancelada. Voltando ao menu principal.")
                return
            altura_valida = validar_altura(altura)
            if not altura_valida:
                print(
                    "Altura inválida. O formato é metros.centímetros. Tente novamente ou 'x' para cancelar.")

        peso_valido = False
        while not peso_valido:
            peso = input("Peso do paciente (em kg): ")
            if peso.lower() == 'x':
                print("Operação cancelada. Voltando ao menu principal.")
                return
            peso_valido = validar_peso(peso)
            if not peso_valido:
                print(
                    "Peso inválido. O formato é quilos.gramas. Tente novamente ou 'x' para cancelar.")

        # frequência de atividades físicas semanal
        frequencia_atividades_sem_opcoes = [
            'ocasionalmente',
            'até 1 vez por semana',
            'até 2 vezes por semana',
            'até 3 vezes por semana',
            'até 4 vezes por semana',
            '5 ou mais vezes por semana'
        ]

        while True:
            print("\nEscolha a frequência de atividades físicas:")
            for i, opcao in enumerate(frequencia_atividades_sem_opcoes, start=0):
                print(f"{i}. {opcao}")

            opcao_escolhida = input("Opção: ")

            if opcao_escolhida.isdigit() and 0 <= int(opcao_escolhida) <= 5:
                frequencia_atividades_sem = int(opcao_escolhida)
                break
            else:
                print(
                    "Opção inválida. Por favor, escolha uma opção de 0 a 5 ou 'x' para voltar ao menu principal.")

        sono_regular = obter_opcao_sim_nao(
            "O paciente possui sono regular? Em torno de 7h/dia?")
        if sono_regular is None:
            return

        # Questão sobre a dieta planejada
        dieta_planejada = obter_opcao_sim_nao(
            "O paciente possui dieta planejada?")
        if dieta_planejada is None:
            return

            # Pergunta sobre o histórico de doenças ou condições específicas
        historico_doencas = input(
            "O paciente possui algum histórico de doenças ou condições específicas? (Limite: 300 caracteres)\n")

        # Validar o comprimento da resposta
        while len(historico_doencas) > 300:
            print("A resposta excede o limite de 300 caracteres.")
            historico_doencas = input(
                "O paciente possui algum histórico de doenças ou condições específicas? (Limite: 300 caracteres)\n")

        # Verifica se os campos obrigatórios não estão em branco
        if not nome_paciente.strip() or not cpf_input.strip() or not endereco.strip():
            print(
                "Não é permitido deixar campos obrigatórios em branco. Registro não criado.")
            return

        # Inserir no banco de dados
        data_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_nascimento_formatada = data_nascimento.strftime("%Y-%m-%d")
        cursor.execute('''
            INSERT INTO cadastro 
            (nome, cpf, data_nascimento, genero, endereco, telefone, pressao_arterial, altura, peso, frequencia_atividades_sem, sono_regular, dieta_planejada, historico_doencas, data_registro) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nome_paciente, cpf_input, data_nascimento_formatada, genero, endereco, telefone, pressao_arterial, altura, peso, frequencia_atividades_sem_opcoes[frequencia_atividades_sem], sono_regular, dieta_planejada, historico_doencas, data_registro))

        conn.commit()

        # Exibir resumo
        cursor.execute('SELECT * FROM cadastro WHERE cpf = ?', (cpf_input,))
        novo_registro = cursor.fetchone()
        registro_interacao = exibir_resumo_registro(cursor, novo_registro)

        # Interagir com a IA
        if registro_interacao:
            interagir_com_ia(registro_interacao)

        logging.info(f"Registro criado com sucesso. CPF: {cpf_input}")
        print("Registro criado com sucesso.")
    except sqlite3.IntegrityError:
        logging.warning(
            f"Tentativa de criar registro com CPF duplicado: {cpf_input}")
        print("Erro ao criar registro: O CPF já está em uso.")
    except sqlite3.Error as e:
        logging.error(f"Erro ao criar registro: {e}")
        print(f"Erro ao criar registro: {e}")



def ler_registros(cursor):
    try:
        cursor.execute("SELECT * FROM cadastro")
        registros = cursor.fetchall()

        for registro in registros:
            print(registro)
    except sqlite3.Error as e:
        print(f"Erro ao ler registros: {e}")


def visualizar_todos_os_registros(cursor, comprimento_maximo_coluna=20):
    try:
        cursor.execute("SELECT * FROM cadastro")
        registros = cursor.fetchall()

        if not registros:
            print("Nenhum registro encontrado.")
            return

        headers = [description[0] for description in cursor.description]
        registros_formatados = []

        for registro in registros:
            registro_formatado = [truncar_string(
                str(campo), comprimento_maximo_coluna) for campo in registro]
            registros_formatados.append(registro_formatado)

        print(tabulate(registros_formatados, headers=headers, tablefmt="pretty"))
    except sqlite3.Error as e:
        print(f"Erro ao visualizar registros: {e}")


def editar_registro(conn, cursor):
    try:
        id_para_atualizar = input(
            "Digite o ID do registro a ser atualizado ('x' para voltar): ")

        if id_para_atualizar.lower() == 'x':
            return

        cursor.execute('SELECT * FROM cadastro WHERE id = ?',
                       (id_para_atualizar,))
        registro = cursor.fetchone()

        if not registro:
            print(f"Registro com ID {id_para_atualizar} não encontrado.")
            return

        print("\nRegistro Atual:")
        headers = [description[0] for description in cursor.description]
        registro_interacao = exibir_resumo_registro(cursor, registro)

        novo_nome_paciente = input("Novo Nome do paciente: ")

        # Verifica se o campo novo_nome_paciente não está em branco
        while not novo_nome_paciente.strip():
            print("Novo Nome do paciente não pode ser deixado em branco.")
            novo_nome_paciente = input("Novo Nome do paciente: ")
            if novo_nome_paciente.lower() == 'x':
                print("Operação cancelada. Voltando ao menu principal.")
                return

        novo_cpf_input = input("Novo CPF do paciente: ")

        while not validar_cpf(novo_cpf_input):
            print(
                "Novo CPF inválido. Por favor, entre com um CPF válido (11 dígitos numéricos) ou 'x' para cancelar.")
            novo_cpf_input = input("Novo CPF do paciente: ")
            if novo_cpf_input.lower() == 'x':
                print("Operação cancelada. Voltando ao menu principal.")
                return

        nova_data_nascimento_str = input(
            "Nova Data de Nascimento (YYYY-MM-DD): ")
        while not validar_data(nova_data_nascimento_str):
            print(
                "Nova Data de Nascimento inválida. Tente novamente ou 'x' para cancelar.")
            nova_data_nascimento_str = input(
                "Nova Data de Nascimento (YYYY-MM-DD): ")
            if nova_data_nascimento_str.lower() == 'x':
                print("Operação cancelada. Voltando ao menu principal.")
                return
        # Convertendo a string para um objeto datetime
        nova_data_nascimento = datetime.strptime(
            nova_data_nascimento_str, "%Y-%m-%d").replace(hour=0, minute=0, second=0)

        novo_genero = input(
            "Novo Gênero (M para Masculino, F para Feminino, N para Não informar): ").upper()

        while novo_genero not in ['M', 'F', 'N']:
            print(
                "Opção inválida. Escolha M para Masculino, F para Feminino, ou N para Não informar.")
            novo_genero = input(
                "Novo Gênero (M para Masculino, F para Feminino, N para Não informar): ").upper()

        novo_endereco = input("Novo Endereço paciente: ")
        # Verifica se o campo novo_endereco não está em branco
        while not novo_endereco.strip():
            print("Novo Endereço paciente não pode ser deixado em branco.")
            novo_endereco = input("Novo Endereço paciente: ")

        novo_telefone = input("Novo Telefone (no formato DDD9numero): ")
        while not validar_telefone(novo_telefone):
            print(
                "Novo Telefone inválido. Tente novamente ou 'x' para cancelar.")
            novo_telefone = input("Novo Telefone (no formato DDD9numero): ")
            if novo_telefone.lower() == 'x':
                print("Operação cancelada. Voltando ao menu principal.")
                return

        # Lógica para pressão arterial
        # Definição das opções de pressão arterial
        pressao_arterial_opcoes = [
            '12/8', '11/7.5', '13/8.5', '12,5/8.8', '14.5/9.5', '15/8.8',
            '16.5/10', '16/11', '19/13', '18/12', '8.5/5.5', '9/6', 'Não listado'
        ]

        opcao_pressao_arterial = obter_opcao(
            "Pressão Arterial", pressao_arterial_opcoes)

        if opcao_pressao_arterial is None:
            nova_pressao_arterial = registro['pressao_arterial']
        else:
            nova_pressao_arterial = opcao_pressao_arterial

        # Altura e Peso
        altura_valida = False
        while not altura_valida:
            nova_altura = input("Nova Altura do paciente (em metros): ")
            if nova_altura.lower() == 'x':
                print("Operação cancelada. Voltando ao menu principal.")
                return
            altura_valida = validar_altura(nova_altura)
            if not altura_valida:
                print(
                    "Altura inválida. O formato é metros.centímetros. Tente novamente ou 'x' para cancelar.")

        peso_valido = False
        while not peso_valido:
            novo_peso = input("Novo Peso do paciente (em kg): ")
            if novo_peso.lower() == 'x':
                print("Operação cancelada. Voltando ao menu principal.")
                return
            peso_valido = validar_peso(novo_peso)
            if not peso_valido:
                print(
                    "Peso inválido. O formato é quilos.gramas. Tente novamente ou 'x' para cancelar.")

        # frequência de atividades físicas semanal
        frequencia_atividades_sem_opcoes = [
            'ocasionalmente',
            'até 1 vez por semana',
            'até 2 vezes por semana',
            'até 3 vezes por semana',
            'até 4 vezes por semana',
            '5 ou mais vezes por semana'
        ]

        while True:
            print("\nEscolha a frequência de atividades físicas:")
            for i, opcao in enumerate(frequencia_atividades_sem_opcoes, start=0):
                print(f"{i}. {opcao}")

            opcao_escolhida = input("Opção: ")

            if opcao_escolhida.isdigit() and 0 <= int(opcao_escolhida) <= 5:
                frequencia_atividades_sem = frequencia_atividades_sem_opcoes[int(
                    opcao_escolhida)]
                break
            else:
                print(
                    "Opção inválida. Por favor, escolha uma opção de 0 a 5 ou 'x' para voltar ao menu principal.")

        sono_regular = obter_opcao_sim_nao(
            "O paciente possui sono regular? Em torno de 7h/dia?")
        if sono_regular is None:
            return

        # Questão sobre a dieta planejada
        dieta_planejada = obter_opcao_sim_nao(
            "O paciente possui dieta planejada?")
        if dieta_planejada is None:
            return

        historico_doencas = input(
            "O paciente possui algum histórico de doenças ou condições específicas? (Limite: 300 caracteres)\n")

        # Validar o comprimento da resposta
        while len(historico_doencas) > 300:
            print("A resposta excede o limite de 300 caracteres.")
            historico_doencas = input(
                "O paciente possui algum histórico de doenças ou condições específicas? (Limite: 300 caracteres)\n")

        # Atualizar no banco de dados, incluindo a nova coluna frequencia_atividades_sem
        cursor.execute('''
            UPDATE cadastro
            SET nome = ?, cpf = ?, data_nascimento = ?, genero = ?, endereco = ?, telefone = ?, 
                pressao_arterial = ?, altura = ?, peso = ?, frequencia_atividades_sem = ?, sono_regular = ?,
                       dieta_planejada = ?, historico_doencas = ? 
            WHERE id = ?
        ''', (novo_nome_paciente, novo_cpf_input, nova_data_nascimento,
              novo_genero, novo_endereco, novo_telefone, nova_pressao_arterial, nova_altura, novo_peso, frequencia_atividades_sem, sono_regular, dieta_planejada, historico_doencas, id_para_atualizar))

        conn.commit()

        # Exibir resumo
        cursor.execute('SELECT * FROM cadastro WHERE id = ?',
                       (id_para_atualizar,))
        registro_atualizado = cursor.fetchone()
        exibir_resumo_registro(cursor, registro_atualizado)

        # Interagir com a IA
        if registro_interacao:
            interagir_com_ia(registro_interacao)

        logging.info(
            f"Registro atualizado com sucesso. ID: {id_para_atualizar}")
        print("Registro atualizado com sucesso.")
    except sqlite3.IntegrityError:
        logging.warning(
            f"Tentativa de atualizar registro com CPF duplicado: {novo_cpf_input}")
        print("Erro ao atualizar registro: O novo CPF já está em uso.")
    except sqlite3.Error as e:
        logging.error(f"Erro ao atualizar registro: {e}")
        print(f"Erro ao atualizar registro: {e}")


def excluir_registro(conn, cursor):
    try:
        id_para_excluir = input(
            "Digite o ID do registro a ser excluído ('x' para voltar): ")

        if id_para_excluir.lower() == 'x':
            return

        cursor.execute('SELECT * FROM cadastro WHERE id = ?',
                       (id_para_excluir,))
        registro = cursor.fetchone()

        if not registro:
            print(f"Registro com ID {id_para_excluir} não encontrado.")
            return

        print("\nRegistro a ser Excluído:")
        headers = [description[0] for description in cursor.description]
        print(tabulate([registro], headers=headers, tablefmt="pretty"))

        confirmacao = input(
            f"Tem certeza de que deseja excluir o registro com ID {id_para_excluir}? (S/N): ").upper()

        if confirmacao != 'S':
            print("Operação cancelada. Voltando ao menu principal.")
            return

        # Excluir no banco de dados
        cursor.execute('DELETE FROM cadastro WHERE id = ?',
                       (id_para_excluir,))

        conn.commit()

        logging.info(f"Registro excluído com sucesso. ID: {id_para_excluir}")
        print("Registro excluído com sucesso.")
    except sqlite3.Error as e:
        logging.error(f"Erro ao excluir registro: {e}")
        print(f"Erro ao excluir registro: {e}")


###          FUNÇÕES DE RELATORIOS        ###

def relatorio_por_genero(cursor, genero):
    try:
        # Converter o gênero para letras maiúsculas
        genero = genero.upper()

        cursor.execute('''
            SELECT * FROM cadastro
            WHERE UPPER(genero) = ?
        ''', (genero,))

        registros = cursor.fetchall()

        if not registros:
            print(f"Nenhum registro encontrado para o gênero '{genero}'.")
            return

        headers = [description[0] for description in cursor.description]
        print(tabulate(registros, headers=headers, tablefmt="pretty"))

        # Criar um diretório 'relatorios' se não existir
        diretorio_relatorios = 'relatorios'
        if not os.path.exists(diretorio_relatorios):
            os.makedirs(diretorio_relatorios)

        # Gerar o caminho do arquivo JSON
        caminho_arquivo_json = os.path.join(
            diretorio_relatorios, f'relatorio_{genero}.json')

        # Salvar os registros em um arquivo JSON
        with open(caminho_arquivo_json, 'w') as arquivo_json:
            registros_dict = [dict(zip(headers, registro))
                              for registro in registros]
            json.dump(registros_dict, arquivo_json, indent=2)

        print(f"Relatório salvo em: {caminho_arquivo_json}")

    except sqlite3.Error as e:
        print(f"Erro ao gerar relatório por gênero: {e}")


def relatorio_por_data(cursor, data_inicial, data_final):
    try:
        # Converter as datas para objetos datetime
        data_inicial_dt = datetime.strptime(data_inicial, "%Y-%m-%d")
        data_final_dt = datetime.strptime(data_final, "%Y-%m-%d")

        # Adicionar a parte de horas, minutos e segundos para incluir o dia inteiro
        data_final_dt = data_final_dt.replace(hour=23, minute=59, second=59)

        cursor.execute('''
            SELECT * FROM cadastro
            WHERE data_registro BETWEEN ? AND ?
        ''', (data_inicial_dt, data_final_dt))

        registros = cursor.fetchall()

        if not registros:
            print("Nenhum registro encontrado para o período especificado.")
            return

        headers = [description[0] for description in cursor.description]
        print(tabulate(registros, headers=headers, tablefmt="pretty"))

        # Criar o diretório "relatórios" se não existir
        if not os.path.exists("relatórios"):
            os.makedirs("relatórios")

        # Criar o arquivo JSON
        nome_arquivo = f"relatórios/relatorio_por_data_{data_inicial}_{data_final}.json"
        with open(nome_arquivo, 'w') as arquivo_json:
            json.dump(registros, arquivo_json, default=str, indent=4)

        print(f"Relatório salvo em {nome_arquivo}")

    except sqlite3.Error as e:
        print(f"Erro ao gerar relatório por data: {e}")


def relatorio_por_local(cursor, local):
    try:
        # Converter o local para letras minúsculas
        local = local.lower()

        cursor.execute('''
            SELECT * FROM cadastro
            WHERE lower(endereco) = ?
        ''', (local,))

        registros = cursor.fetchall()

        if not registros:
            print(f"Nenhum registro encontrado para o local '{local}'.")
            return

        headers = [description[0] for description in cursor.description]
        print(tabulate(registros, headers=headers, tablefmt="pretty"))

        # Criar um diretório 'relatorios' se não existir
        diretorio_relatorios = 'relatorios'
        if not os.path.exists(diretorio_relatorios):
            os.makedirs(diretorio_relatorios)

        # Gerar o caminho do arquivo JSON
        caminho_arquivo_json = os.path.join(
            diretorio_relatorios, f'relatorio_{local}.json')

        # Salvar os registros em um arquivo JSON
        with open(caminho_arquivo_json, 'w') as arquivo_json:
            registros_dict = [dict(zip(headers, registro))
                              for registro in registros]
            json.dump(registros_dict, arquivo_json, indent=2)

        print(f"Relatório salvo em: {caminho_arquivo_json}")

    except sqlite3.Error as e:
        print(f"Erro ao gerar relatório por local: {e}")


###         CONEXÃO COM IA            ###


###         VERIFICAÇÕES E MENU         ###


def exibir_status_bd():
    if os.path.exists('database//atendimento_medico.db'):
        print("Banco de dados carregado.")
    else:
        print("Banco de dados está sendo gerado para a operação.")


def exibir_menu(conn, cursor):
    menu_opcoes = [
        {"Opção": '1', "Descrição": "Criar Registro"},
        {"Opção": '2', "Descrição": "Ler Registros"},
        {"Opção": '3', "Descrição": "Visualizar Todos os Registros"},
        {"Opção": '4', "Descrição": "Atualizar Registro"},
        {"Opção": '5', "Descrição": "Excluir Registro"},
        {"Opção": '6', "Descrição": "Sair"},
        {"Opção": '7', "Descrição": "Ajuda - Mostra informações sobre como usar o programa."},
        {"Opção": '8', "Descrição": "Gerar Relatórios"}
    ]

    print("\nMenu:")
    print(tabulate(menu_opcoes, headers="keys", tablefmt="pretty"))

    while True:
        escolha = input("Escolha uma opção ('x' para voltar): ")

        if escolha.lower() == 'x':
            print("Voltando ao menu principal.")
            return 'x'

        if escolha.isdigit():
            escolha = int(escolha)

            if 1 <= escolha <= 8:  # número de opções no menu
                if escolha == 8:
                    gerar_relatorios_menu(conn, cursor)
                else:
                    return str(escolha)
            else:
                print("Opção inválida. Deve ser um número entre 1 e 8.")
        else:
            print("Opção inválida. Deve ser um número inteiro ou 'x' para voltar.")


def gerar_relatorios_menu(conn, cursor):
    while True:
        print("\nRelatórios:")
        print("1. Relatório por Data")
        print("2. Relatório por Local")
        print("3. Relatório por Gênero")
        print("4. Voltar")

        opcao_relatorio = input("Escolha uma opção de relatório: ")

        if opcao_relatorio == '1':
            data_inicial = input("Digite a data inicial (YYYY-MM-DD): ")
            data_final = input("Digite a data final (YYYY-MM-DD): ")

            if validar_data(data_inicial) and validar_data(data_final):
                relatorio_por_data(cursor, data_inicial, data_final)
            else:
                print("Datas inválidas. Tente novamente.")
        elif opcao_relatorio == '2':
            local = input("Digite o local para o relatório: ")

            if validar_local(local):
                relatorio_por_local(cursor, local)
            else:
                print("Local inválido. Tente novamente.")
        elif opcao_relatorio == '3':
            genero = input("Digite o gênero para o relatório (M, F, N): ")

            if validar_genero(genero):
                relatorio_por_genero(cursor, genero)
            else:
                print("Gênero inválido. Tente novamente.")
        elif opcao_relatorio == '4':
            print("Voltando ao menu principal.")

            menu_opcoes = [
                {"Opção": '1', "Descrição": "Criar Registro"},
                {"Opção": '2', "Descrição": "Ler Registros"},
                {"Opção": '3', "Descrição": "Visualizar Todos os Registros"},
                {"Opção": '4', "Descrição": "Atualizar Registro"},
                {"Opção": '5', "Descrição": "Excluir Registro"},
                {"Opção": '6', "Descrição": "Sair"},
                {"Opção": '7', "Descrição": "Ajuda - Mostra informações sobre como usar o programa."},
                {"Opção": '8', "Descrição": "Gerar Relatórios"}
            ]
            print("\nMenu:")
            print(tabulate(menu_opcoes, headers="keys", tablefmt="pretty"))

            break
        else:
            print("Opção inválida. Tente novamente.")


def exibir_ajuda():
    print("\nBem-vindo ao assistente médico Bet on Tech.\n")
    print("Este programa permite a gestão de registros de pacientes. Utilize as seguintes opções:")
    print("1. 'Criar Registro': Adiciona um novo paciente ao sistema.")
    print("2. 'Ler Registros': Exibe todos os pacientes cadastrados.")
    print("3. 'Visualizar Todos os Registros': Mostra todos os pacientes em formato tabular.")
    print("4. 'Atualizar Registro': Permite a atualização de informações de um paciente.")
    print("5. 'Excluir Registro': Remove um paciente da base de dados.")
    print("6. 'Sair': Encerra o programa.")
    print("7. 'Ajuda': Mostra estas informações novamente.")
    print("8. 'Gerar Relatórios': Gera relatórios com base em diferentes critérios.")


def exibir_ajuda():
    print("\nBem-vindo ao assistente médico Bet on Tech.\n")
    print("Este programa permite a gestão de registros de pacientes. Utilize as seguintes opções:")
    print("1. 'Criar Registro': Adiciona um novo paciente ao sistema.")
    print("2. 'Ler Registros': Exibe todos os pacientes cadastrados.")
    print("3. 'Visualizar Todos os Registros': Mostra todos os pacientes em formato tabular.")
    print("4. 'Atualizar Registro': Permite a atualização de informações de um paciente.")
    print("5. 'Excluir Registro': Remove um paciente da base de dados.")
    print("6. 'Sair': Encerra o programa.")
    print("7. 'Ajuda': Mostra estas informações novamente.")
    print("8. 'Gerar Relatórios': Gera relatórios com base em diferentes critérios.")


def main():
    print("Bem-vindo ao assistente médico Bet on Tech.")

    try:
        with conectar_bd() as conn, conn:
            cursor = conn.cursor()

            exibir_status_bd()
            executar_setup(cursor)

            while True:
                escolha = exibir_menu(conn, cursor)

                if escolha == '1':
                    criar_registro(conn, cursor)
                elif escolha == '2':
                    ler_registros(cursor)
                elif escolha == '3':
                    visualizar_todos_os_registros(cursor)
                elif escolha == '4':
                    editar_registro(conn, cursor)
                elif escolha == '5':
                    excluir_registro(conn, cursor)
                elif escolha == '6':
                    print("Saindo...")
                    break
                elif escolha == '7':
                    exibir_ajuda()
                elif escolha == '8':
                    data_inicial = obter_data_valida(
                        "Digite a data inicial (YYYY-MM-DD): ")
                    data_final = obter_data_valida(
                        "Digite a data final (YYYY-MM-DD): ")
                    relatorio_por_data(cursor, data_inicial, data_final)
                else:
                    print("Opção inválida. Tente novamente.")

            print("Programa encerrado.")

    except sqlite3.Error as e:
        logging.error(f"Erro durante a execução do programa: {e}")
        print(f"Erro durante a execução do programa: {e}")


if __name__ == "__main__":
    main()
