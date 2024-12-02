import requests
import ast
from flask import Flask, request, jsonify, render_template
from datetime import datetime
from flask_socketio import SocketIO, emit
import subprocess

app = Flask(__name__)
socketio = SocketIO(app)

def pipefy_send(query):
    url = "https://api.pipefy.com/graphql"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": "Bearer eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJQaXBlZnkiLCJpYXQiOjE2OTMzMTE3NTgsImp0aSI6ImE0OGU0MjIxLTE5ODMtNDgyOC1hY2E0LTk3M2FjMDgxYjljZiIsInN1YiI6MzAyNDg4MjU2LCJ1c2VyIjp7ImlkIjozMDI0ODgyNTYsImVtYWlsIjoiY2Fpby5wYWdsaWFyYW5pQGFtbGFicy5jb20uYnIiLCJhcHBsaWNhdGlvbiI6MzAwMjcxMjAyLCJzY29wZXMiOltdfSwiaW50ZXJmYWNlX3V1aWQiOm51bGx9.amWFG4ywllqfP7AK8tYwEZ-Z8LlCrnnOe6UBjHxhq3GGOX9n3c8CU3QIAPoCd-4vRIaY2p35Gndrn9oMFnAy5g"
    }
    response = requests.post(url, json={"query": query}, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Erro na chamada da API do Pipefy: {response.status_code}", "details": response.text}

def converter_tempo(segundos):
    seconds_per_day = 86400
    seconds_per_hour = 3600
    seconds_per_minute = 60
    
    dias = segundos // seconds_per_day
    segundos_restantes = segundos % seconds_per_day
    
    horas = segundos_restantes // seconds_per_hour
    segundos_restantes %= seconds_per_hour
    
    minutos = segundos_restantes // seconds_per_minute
    segundos_finais = segundos_restantes % seconds_per_minute
    
    return f"{dias}d {horas}h {minutos}m {segundos_finais}s"

def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

def mutation_card(card_id, field_id, value):
    mutation_query = f"""
    mutation {{
        updateCardField(input: {{card_id: {card_id}, field_id: "{field_id}", new_value: ["{value}"]}}) {{
            clientMutationId
            success
        }}
    }}
    """
    log = pipefy_send(mutation_query)
    print(log)

def query_E02():
    o_que_quero_E02 = {
        "id_do_pedido",
        "data_do_pedido_1",
        "phase_id",
        "quantos_kits_nano_market_deseja_1",
        "quantos_nano_market",
        "nano_market_completo",
        "quantos",
        "quantidade_de_kit_completo_trava_de_geladeira",
        "quantos_kits_nano_market_completo",
        "quantas_travas_mec_nicas_para_geladeira_voc_deseja",
        "quantidade_de_adaptadores",
        "quantidade_de_adaptadores_micro_market_troca",
        "quantidade_de_m_dulo_controle_de_acesso_geladeira_individual",
        "quantidade_de_m_dulo_trava_de_at_4_geladeiras",
        "quantidade_de_m_dulo_controle_de_acesso_para_geladeira_individual",
        "quantidade_de_m_dulo_de_acesso_de_at_4_geladeiras",
        "quantidade_de_m_dulo_de_acesso_geladeira_troca",
        "quantidade_de_m_dulo_de_trava_de_at_4_geladeiras_troca",
        "quantidade_de_moderninha_smart_troca",
        "quantidade_de_eletroim",
        "o_pedido_ser",
        "id_da_nota_de_envio",
        "status_da_nota",
        "nota_fiscal",
        "etiqueta_dos_correios",
        "pedido_c_exce_o",
        "responsible_card",
    }

    fases = {
        '13 - Montagem': 311237011,
        '14 - Lançar S/N': 311731503,
        '15 - Preparação': 311731510,
        '17 - Checklist final': 321289037,
        '18 - Aguardando Embalagem': 311297630,
        '19 - Liberado para retirada': 311255161,
        'ERRO/CORREÇÃO': 325993095,
    }

    results = []

    for phase_name, phase_id in fases.items():
        query = f"""query MyQuery {{
                        phase(id: "{phase_id}") {{
                            cards {{
                                edges {{
                                    node {{
                                        title
                                        id
                                        labels {{
                                            name
                                        }}
                                        fields {{
                                            name
                                            value
                                            field {{
                                                id
                                            }}
                                        }}
                                        current_phase_age
                                    }}
                                }}
                            }}
                        }}
                    }}
                """
        response = pipefy_send(query)
        if "error" in response:
            return response

        cards = response["data"]["phase"]["cards"]["edges"]

        for card in cards:
            card_id = card["node"]["id"]
            card_title = card["node"]["title"]
            card_labels = [label["name"] for label in card["node"]["labels"]]
            card_fields_data = {}
            card_time_bruto = card["node"]["current_phase_age"]

            tempo_na_fase = converter_tempo(card_time_bruto)

            for field in card["node"]["fields"]:
                field_id = field["field"]["id"]
                field_name = field["name"]
                field_value = field["value"]

                if field_id in o_que_quero_E02:
                    card_fields_data[field_id] = field_value

            data_do_pedido = card_fields_data.get("data_do_pedido_1", "")
            nota_fiscal_bruto = card_fields_data.get("nota_fiscal", "")
            etiqueta_dos_correios_bruto = card_fields_data.get("etiqueta_dos_correios", "")

            # Remove caracteres especificados dos links
            def clean_link(link):
                return link.replace('[', '').replace(']', '').replace('"', '')

            # Verifica se nota_fiscal_bruto é uma lista e trata adequadamente
            if isinstance(nota_fiscal_bruto, list):
                nota_fiscal = ", ".join([clean_link(url) for url in nota_fiscal_bruto])
            else:
                nota_fiscal = clean_link(nota_fiscal_bruto)

            # Verifica se etiqueta_dos_correios_bruto é uma lista e trata adequadamente
            if isinstance(etiqueta_dos_correios_bruto, list):
                etiqueta_dos_correios = ", ".join([clean_link(url) for url in etiqueta_dos_correios_bruto])
            else:
                etiqueta_dos_correios = clean_link(etiqueta_dos_correios_bruto)

            print("Isto é o link da nota fiscal: ", nota_fiscal)
            print("Isto é o link da nota fiscal bruto: ", nota_fiscal_bruto)

            if data_do_pedido:
                try:
                    data_do_pedido = datetime.strptime(data_do_pedido, "%m/%d/%Y")
                    dias_passados = (datetime.today() - data_do_pedido).days + 1
                except ValueError:
                    dias_passados = "Data inválida"
            else:
                dias_passados = "Data não fornecida"

            results.append({
                # Informações padrão do pedido
                "ID": card_id,
                "Etiquetas": card_labels,
                "Título": card_title,
                "Fase": phase_name,
                "Tipo de envio": card_fields_data.get("o_pedido_ser", ""),
                "Tempo na fase atual": tempo_na_fase,
                "Dias": dias_passados,
                "Setor": "PRODUÇÃO",
                "Pipe": "E02",
                "Responsavel": "",
                "Exceção": card_fields_data.get("pedido_c_exce_o", ""),
                "Nota fiscal": nota_fiscal,
                "Etiqueta dos Correios": etiqueta_dos_correios,
                "Responsavel do pedido": card_fields_data.get("responsible_card", ""),
                # Quantidades de itens
                "Kits Nano Market": safe_int(card_fields_data.get("quantos_kits_nano_market_deseja_1", "0")),
                "Nano Market Completo": safe_int(card_fields_data.get("nano_market_completo", "0")),
                "Quantidade de Kits Completo Trava de Geladeira": safe_int(card_fields_data.get("quantidade_de_kit_completo_trava_de_geladeira", "0")),
                "Quantidade de Kits Nano Market Completo": safe_int(card_fields_data.get("quantos_kits_nano_market_completo", "0")),
                "Quantidade de Travas Mecânicas": safe_int(card_fields_data.get("quantas_travas_mec_nicas_para_geladeira_voc_deseja", "0")),
                "Quantidade de Adaptadores": safe_int(card_fields_data.get("quantidade_de_adaptadores", "0")),
                "Quantidade de Adaptadores Micro Market": safe_int(card_fields_data.get("quantidade_de_adaptadores_micro_market_troca", "0")),
                "Quantidade de Módulo Controle de Acesso Geladeira Individual": safe_int(card_fields_data.get("quantidade_de_m_dulo_controle_de_acesso_geladeira_individual", "0")),
                "Quantidade de Módulo de Trava de Geladeira 4 Vias": safe_int(card_fields_data.get("quantidade_de_m_dulo_de_trava_de_at_4_geladeiras_troca", "0")),
                "Quantidade de Moderninha Smart": safe_int(card_fields_data.get("quantidade_de_moderninha_smart_troca", "0")),
                "Quantidade de Eletroim": safe_int(card_fields_data.get("quantidade_de_eletroim", "0")),
            })

    return results

def query_Trocas():
    o_que_quero_trocas = {
        "id_do_card",
        "data_do_pedido",
        "quantos_kits_nano_market_deseja_1",
        "quantos_nano_market",
        "nano_market_completo",
        "quantos",
        "quantidade_de_kit_completo_trava_de_geladeira",
        "quantos_kits_nano_market_completo",
        "quantidade_de_trava_m_canica",
        "quantidade_de_adaptadores",
        "quantidade_de_adaptadores_micro_market_troca",
        "quantidade_de_m_dulo_de_acesso_geladeira",
        "quantidade_de_m_dulo_para_4_geladeiras",
        "quantidade_de_m_dulo_controle_de_acesso_para_geladeira_individual",
        "quantidade_de_m_dulo_de_acesso_de_at_4_geladeiras",
        "quantidade_de_m_dulo_de_acesso_geladeira_troca",
        "quantidade_de_m_dulo_de_trava_de_at_4_geladeiras_troca",
        "quantidade_de_moderninha_smart_2",
        "quantidade_de_moderninha_smart_1",
        "quantidade_de_eletroim",
        "ntrega_via_correios_ou_ser_o_retirados_na_amlabs",
        "id_da_nota_de_envio",
        "status_da_nota",
        "nota_fiscal",
        "etiqueta_dos_correios",
        "responsible_card",
    }

    fases = {
        'Confirmar Endereço': 321546412,
        'Montagem': 321546413,
        'Lançar SN': 328615023,
        'Preparação': 328615038,
        'Checklist': 329247774,
    }

    results = []

    for phase_name, phase_id in fases.items():
        query = f"""query MyQuery {{
                        phase(id: "{phase_id}") {{
                            cards {{
                                edges {{
                                    node {{
                                        title
                                        id
                                        labels {{
                                            name
                                        }}
                                        fields {{
                                            name
                                            value
                                            field {{
                                                id
                                            }}
                                        }}
                                        current_phase_age
                                    }}
                                }}
                            }}
                        }}
                    }}
                """
        response = pipefy_send(query)
        if "error" in response:
            return response

        cards = response["data"]["phase"]["cards"]["edges"]

        for card in cards:
            card_id = card["node"]["id"]
            card_title = card["node"]["title"]
            card_labels = [label["name"] for label in card["node"]["labels"]]
            card_fields_data = {}
            card_time_bruto = card["node"]["current_phase_age"]

            tempo_na_fase = converter_tempo(card_time_bruto)

            for field in card["node"]["fields"]:
                field_id = field["field"]["id"]
                field_name = field["name"]
                field_value = field["value"]

                if field_id in o_que_quero_trocas:
                    card_fields_data[field_id] = field_value

            data_do_pedido = card_fields_data.get("data_do_pedido", "")
            nota_fiscal_bruto = card_fields_data.get("nota_fiscal", "")
            etiqueta_dos_correios_bruto = card_fields_data.get("etiqueta_dos_correios", "")

            # Remove caracteres especificados dos links
            def clean_link(link):
                return link.replace('[', '').replace(']', '').replace('"', '')

            # Verifica se nota_fiscal_bruto é uma lista e trata adequadamente
            if isinstance(nota_fiscal_bruto, list):
                nota_fiscal = ", ".join([clean_link(url) for url in nota_fiscal_bruto])
            else:
                nota_fiscal = clean_link(nota_fiscal_bruto)

            # Verifica se etiqueta_dos_correios_bruto é uma lista e trata adequadamente
            if isinstance(etiqueta_dos_correios_bruto, list):
                etiqueta_dos_correios = ", ".join([clean_link(url) for url in etiqueta_dos_correios_bruto])
            else:
                etiqueta_dos_correios = clean_link(etiqueta_dos_correios_bruto)

            print("Isto é o link da nota fiscal: ", nota_fiscal)
            print("Isto é o link da nota fiscal bruto: ", nota_fiscal_bruto)

            if data_do_pedido:
                try:
                    data_do_pedido = datetime.strptime(data_do_pedido, "%m/%d/%Y")
                    dias_passados = (datetime.today() - data_do_pedido).days + 1
                except ValueError:
                    dias_passados = "Data inválida"
            else:
                dias_passados = "Data não fornecida"

            results.append({
                # Informações padrão do pedido
                "ID": card_id,
                "Etiquetas": card_labels,
                "Título": card_title,
                "Fase": phase_name,
                "Tipo de envio": card_fields_data.get("ntrega_via_correios_ou_ser_o_retirados_na_amlabs", ""),
                "Tempo na fase atual": tempo_na_fase,
                "Dias": dias_passados,
                "Setor": "SUPORTE",
                "Pipe": "TA",
                "Responsavel": "",
                "Nota fiscal": nota_fiscal,
                "Etiqueta dos Correios": etiqueta_dos_correios,
                "Responsavel do pedido": card_fields_data.get("responsible_card", ""),
                # Quantidades de itens
                "Kits Nano Market": safe_int(card_fields_data.get("quantos_kits_nano_market_deseja_1", "0")),
                "Nano Market Completo": safe_int(card_fields_data.get("nano_market_completo", "0")),
                "Quantidade de Kits Completo Trava de Geladeira": safe_int(card_fields_data.get("quantidade_de_kit_completo_trava_de_geladeira", "0")),
                "Quantidade de Kits Nano Market Completo": safe_int(card_fields_data.get("quantos_kits_nano_market_completo", "0")),
                "Quantidade de Travas Mecânicas": safe_int(card_fields_data.get("quantidade_de_trava_m_canica", "0")),
                "Quantidade de Adaptadores": safe_int(card_fields_data.get("quantidade_de_adaptadores", "0")),
                "Quantidade de Adaptadores Micro Market": safe_int(card_fields_data.get("quantidade_de_adaptadores_micro_market_troca", "0")),
                "Quantidade de Módulo Controle de Acesso Geladeira Individual": safe_int(card_fields_data.get("quantidade_de_m_dulo_controle_de_acesso_para_geladeira_individual", "0")),
                "Quantidade de Módulo de Trava de Geladeira 4 Vias": safe_int(card_fields_data.get("quantidade_de_m_dulo_de_acesso_de_at_4_geladeiras", "0")),
                "Quantidade de Moderninha Smart 1": safe_int(card_fields_data.get("quantidade_de_moderninha_smart_1", "0")),
                "Quantidade de Moderninha Smart 2": safe_int(card_fields_data.get("quantidade_de_moderninha_smart_2", "0")),
                "Quantidade de Eletroima": safe_int(card_fields_data.get("quantidade_de_eletroim", "0")),
            })

    return results

def query_E01():
    o_que_quero_E01 = {
        "id_t_tulo",
        "pedido_c_exce_o",
        "data_do_pedido",
        "quantos_kits_nano_market_deseja_1",
        "quantos_nano_market",
        "nano_market_completo",
        "quantos",
        "quantidade_de_kit_completo_trava_de_geladeira",
        "quantos_kits_nano_market_completo",
        "quantidade_de_trava_m_canica",
        "quantidade_de_adaptadores",
        "quantidade_de_adaptadores_micro_market_troca",
        "quantidade_de_m_dulo_de_acesso_geladeira",
        "quantidade_de_m_dulo_para_4_geladeiras",
        "quantidade_de_m_dulo_controle_de_acesso_para_geladeira_individual",
        "quantidade_de_m_dulo_de_acesso_de_at_4_geladeiras",
        "quantidade_de_m_dulo_de_acesso_geladeira_troca",
        "quantidade_de_m_dulo_de_trava_de_at_4_geladeiras_troca",
        "quantidade_de_moderninha_smart_2",
        "quantidade_de_moderninha_smart_1",
        "quantidade_de_eletroim",
        "copy_of_primeiro_pedido",
        "id_da_nota_de_envio",
        "status_da_nota",
        "nota_fical",
        "etiqueta_a_confirmar",
        "responsible_card",
        "entrega_via_correios_ou_ser_o_retirados_na_amlabs",
    }

    fases = {
        'ERRO': 325318671,
        '02 - Cadastro no Omie': 311815660,
        '03 - Geração de boleto': 311503491,
        '04 - Conferir Conta PAGSEGURO': 311259024,
        '05 - Criar Conta PAGSEGURO': 311259021,
        '06 - Gerar Etiqueta': 311913416,
        '07 - Ag. Código de Ativação PAGSEGURO': 311259020,
        '08 - Lançar SN': 311913432,
        '09 - Gerar contrato': 318519144,
        '10 - Pagamento': 318519151,
        '11 - Aguardando assinatura': 311913453,
        '12- Gerar Nota Fiscal': 311967060,
        '13 - Confirmação de Etiqueta': 325278488,
        '18 - Criar cards filho': 327697690,
    }

    etiquetas_serviços = {
        'ASSISTÊNCIA': 305464726,
        'ATUALIZAR': 305622614,
        'PENDENTE': 305828491,
        'ATIVAÇÃO': 306531070,
        'TROCA DE TITULARIDADE': 306953462,
        'NFC-e': 307035722,
        'ALERTA DE DESVIOS': 307057647,
        'DEMONSTRAÇÃO': 307133254,
        'IMPLANTAÇÃO DO OMIE': 307716622,
        'TREINAMENTO PRESENCIAL': 307722400,
        'ADAPTADOR': 308334638,
        'Teste': 308658042,
        '07-LAUDO': 308702211,
        'CRIAÇÃO DE AMBIENTE': 308750250,
        '10 - ATUALIZAÇÃO DO AMBIENTE': 309208863,
        '11 - ATUALIZAÇÃO PAGSEGURO': 309208882,
        'Em Atualização de Fluxo (Provisório)': 309256730,
        '12 - CASHLESS': 309425221,
        '15 - CRIAR AMBIENTE DE FRANQUIA': 310193326,
        '18 - ESTOQUE CENTRAL': 310654736,
        'Token API': 310876066,
        '17 - White Label': 310970433,
        'Be Honest - Serviços': 310992210,
        'Ingresso Summit': 311072047,
        '.': 311132399,
        '19 - CLIENTE NOVO': 311781727,
    }

    results = []

    unique_cards = set()

    for phase_name, phase_id in fases.items():
        query = f"""
        query MyQuery {{
            phase(id: "{phase_id}") {{
                cards {{
                    edges {{
                        node {{
                            title
                            id
                            labels {{ name }}
                            fields {{ name value field {{ id }} }}
                            current_phase_age
                        }}
                    }}
                }}
            }}
        }}
        """
        response = pipefy_send(query)
        if "error" in response:
            return response

        cards = response["data"]["phase"]["cards"]["edges"]
        for card in cards:
            card_id = card["node"]["id"]
            if card_id in unique_cards:
                continue
            unique_cards.add(card_id)

            card_title = card["node"]["title"]
            card_labels = [label["name"] for label in card["node"]["labels"]]
            card_fields_data = {}
            card_time_bruto = card["node"]["current_phase_age"]

            # Verificação das etiquetas
            if any(label in etiquetas_serviços for label in card_labels):
                print(f"Card com etiqueta excluída encontrado: {card_title}, pulando para o próximo card...")
                continue

            tempo_na_fase = converter_tempo(card_time_bruto)
            for field in card["node"]["fields"]:
                field_id = field["field"]["id"]
                field_name = field["name"]
                field_value = field["value"]
                if field_id in o_que_quero_E01:
                    card_fields_data[field_id] = field_value

            data_do_pedido = card_fields_data.get("data_do_pedido", "")
            nota_fiscal_bruto = card_fields_data.get("nota_fical", "")
            etiqueta_dos_correios_bruto = card_fields_data.get("etiqueta_a_confirmar", "")

            # Remove caracteres especificados dos links
            def clean_link(link):
                return link.replace('[', '').replace(']', '').replace('"', '')

            # Verifica se nota_fiscal_bruto é uma lista e trata adequadamente
            if isinstance(nota_fiscal_bruto, list):
                nota_fiscal = ", ".join([clean_link(url) for url in nota_fiscal_bruto])
            else:
                nota_fiscal = clean_link(nota_fiscal_bruto)

            # Verifica se etiqueta_dos_correios_bruto é uma lista e trata adequadamente
            if isinstance(etiqueta_dos_correios_bruto, list):
                etiqueta_dos_correios = ", ".join([clean_link(url) for url in etiqueta_dos_correios_bruto])
            else:
                etiqueta_dos_correios = clean_link(etiqueta_dos_correios_bruto)

            print("Isto é o link da nota fiscal: ", nota_fiscal)
            print("Isto é o link da nota fiscal bruto: ", nota_fiscal_bruto)

            if data_do_pedido:
                try:
                    data_do_pedido = datetime.strptime(data_do_pedido, "%m/%d/%Y")
                    dias_passados = (datetime.today() - data_do_pedido).days + 1
                except ValueError:
                    dias_passados = "Data inválida"
            else:
                dias_passados = "Data não fornecida"

            results.append({
                # Informações padrão do pedido
                "ID": card_id,
                "Etiquetas": card_labels,
                "Título": card_title,
                "Fase": phase_name,
                "Tipo de envio": card_fields_data.get("entrega_via_correios_ou_ser_o_retirados_na_amlabs", ""),
                "Tempo na fase atual": tempo_na_fase,
                "Dias": dias_passados,
                "Setor": "ADMINISTRATIVO",
                "Pipe": "E01",
                "Responsavel": "",
                "Exceção": card_fields_data.get("pedido_c_exce_o", ""),
                "Nota fiscal": nota_fiscal,
                "Etiqueta dos Correios": etiqueta_dos_correios,
                "Responsavel do pedido": card_fields_data.get("responsible_card", ""),
                # Quantidades de itens
                "Kits Nano Market": safe_int(card_fields_data.get("quantos_kits_nano_market_deseja_1", "0")),
                "Nano Market Completo": safe_int(card_fields_data.get("nano_market_completo", "0")),
                "Quantidade de Kits Completo Trava de Geladeira": safe_int(card_fields_data.get("quantidade_de_kit_completo_trava_de_geladeira", "0")),
                "Quantidade de Kits Nano Market Completo": safe_int(card_fields_data.get("quantos_kits_nano_market_completo", "0")),
                "Quantidade de Travas Mecânicas": safe_int(card_fields_data.get("quantas_travas_mec_nicas_para_geladeira_voc_deseja", "0")),
                "Quantidade de Adaptadores": safe_int(card_fields_data.get("quantidade_de_adaptadores", "0")),
                "Quantidade de Adaptadores Micro Market": safe_int(card_fields_data.get("quantidade_de_adaptadores_micro_market_troca", "0")),
                "Quantidade de Módulo Controle de Acesso Geladeira Individual": safe_int(card_fields_data.get("quantidade_de_m_dulo_controle_de_acesso_geladeira_individual", "0")),
                "Quantidade de Módulo de Trava de Geladeira 4 Vias": safe_int(card_fields_data.get("quantidade_de_m_dulo_de_trava_de_at_4_geladeiras_troca", "0")),
                "Quantidade de Moderninha Smart": safe_int(card_fields_data.get("quantidade_de_moderninha_smart_troca", "0")),
                "Quantidade de Eletroim": safe_int(card_fields_data.get("quantidade_de_eletroim", "0")),
            })

    return results

def query_P8():
    o_que_quero_P8 = {
        "id_do_pedido",
        "pedido_c_exce_o",
        "data_do_pedido",
        "quantos_kits_nano_market_deseja_1",
        "quantos_nano_market",
        "nano_market_completo",
        "quantos",
        "quantidade_de_kit_completo_trava_de_geladeira",
        "quantos_kits_nano_market_completo",
        "quantidade_de_trava_m_canica",
        "quantidade_de_adaptadores",
        "quantidade_de_adaptadores_micro_market_troca",
        "quantidade_de_m_dulo_de_acesso_geladeira",
        "quantidade_de_m_dulo_para_4_geladeiras",
        "quantidade_de_m_dulo_controle_de_acesso_para_geladeira_individual",
        "quantidade_de_m_dulo_de_acesso_de_at_4_geladeiras",
        "quantidade_de_m_dulo_de_acesso_geladeira_troca",
        "quantidade_de_m_dulo_de_trava_de_at_4_geladeiras_troca",
        "quantidade_de_moderninha_smart_2",
        "quantidade_de_moderninha_smart_1",
        "quantidade_de_eletroim",
        "seu_primeiro_pedido_com_o_cnpj_acima",
        "id_da_nota_de_envio",
        "status_da_nota",
        "nota_fical",
        "etiqueta_a_confirmar",
        "responsible_card",
        "entrega_via_correios_ou_ser_o_retirados_na_amlabs",
    }

    fases = {
        'ERRO': 325318671,
        '02 - Cadastro no Omie': 311815660,
        '03 - Geração de boleto': 311503491,
        '04 - Conferir Conta PAGSEGURO': 311259024,
        '05 - Criar Conta PAGSEGURO': 311259021,
        '06 - Gerar Etiqueta': 311913416,
        '07 - Ag. Código de Ativação PAGSEGURO': 311259020,
        '08 - Lançar SN': 311913432,
        '09 - Gerar contrato': 318519144,
        '10 - Pagamento': 318519151,
        '11 - Aguardando assinatura': 311913453,
        '12- Gerar Nota Fiscal': 311967060,
        '13 - Confirmação de Etiqueta': 325278488,
        '18 - Criar cards filho': 327697690,
    }

    etiquetas_serviços = {
        'ASSISTÊNCIA': 305464726,
        'ATUALIZAR': 305622614,
        'PENDENTE': 305828491,
        'ATIVAÇÃO': 306531070,
        'TROCA DE TITULARIDADE': 306953462,
        'NFC-e': 307035722,
        'ALERTA DE DESVIOS': 307057647,
        'DEMONSTRAÇÃO': 307133254,
        'IMPLANTAÇÃO DO OMIE': 307716622,
        'TREINAMENTO PRESENCIAL': 307722400,
        'ADAPTADOR': 308334638,
        'Teste': 308658042,
        '07-LAUDO': 308702211,
        'CRIAÇÃO DE AMBIENTE': 308750250,
        '10 - ATUALIZAÇÃO DO AMBIENTE': 309208863,
        '11 - ATUALIZAÇÃO PAGSEGURO': 309208882,
        'Em Atualização de Fluxo (Provisório)': 309256730,
        '12 - CASHLESS': 309425221,
        '15 - CRIAR AMBIENTE DE FRANQUIA': 310193326,
        '18 - ESTOQUE CENTRAL': 310654736,
        'Token API': 310876066,
        '17 - White Label': 310970433,
        'Be Honest - Serviços': 310992210,
        'Ingresso Summit': 311072047,
        '.': 311132399,
        '19 - CLIENTE NOVO': 311781727,
    }

    results = []

    unique_cards = set()

    for phase_name, phase_id in fases.items():
        query = f"""
        query MyQuery {{
            phase(id: "{phase_id}") {{
                cards {{
                    edges {{
                        node {{
                            title
                            id
                            labels {{ name }}
                            fields {{ name value field {{ id }} }}
                            current_phase_age
                        }}
                    }}
                }}
            }}
        }}
        """
        response = pipefy_send(query)
        if "error" in response:
            return response

        cards = response["data"]["phase"]["cards"]["edges"]
        for card in cards:
            card_id = card["node"]["id"]
            if card_id in unique_cards:
                continue
            unique_cards.add(card_id)

            card_title = card["node"]["title"]
            card_labels = [label["name"] for label in card["node"]["labels"]]
            card_fields_data = {}
            card_time_bruto = card["node"]["current_phase_age"]

            # Verificação das etiquetas
            if any(label in etiquetas_serviços for label in card_labels):
                print(f"Card com etiqueta excluída encontrado: {card_title}, pulando para o próximo card...")
                continue

            tempo_na_fase = converter_tempo(card_time_bruto)
            for field in card["node"]["fields"]:
                field_id = field["field"]["id"]
                field_name = field["name"]
                field_value = field["value"]
                if field_id in o_que_quero_P8:
                    card_fields_data[field_id] = field_value

            data_do_pedido = card_fields_data.get("data_do_pedido", "")
            nota_fiscal_bruto = card_fields_data.get("nota_fical", "")
            etiqueta_dos_correios_bruto = card_fields_data.get("etiqueta_a_confirmar", "")

            # Remove caracteres especificados dos links
            def clean_link(link):
                return link.replace('[', '').replace(']', '').replace('"', '')

            # Verifica se nota_fiscal_bruto é uma lista e trata adequadamente
            if isinstance(nota_fiscal_bruto, list):
                nota_fiscal = ", ".join([clean_link(url) for url in nota_fiscal_bruto])
            else:
                nota_fiscal = clean_link(nota_fiscal_bruto)

            # Verifica se etiqueta_dos_correios_bruto é uma lista e trata adequadamente
            if isinstance(etiqueta_dos_correios_bruto, list):
                etiqueta_dos_correios = ", ".join([clean_link(url) for url in etiqueta_dos_correios_bruto])
            else:
                etiqueta_dos_correios = clean_link(etiqueta_dos_correios_bruto)

            print("Isto é o link da nota fiscal: ", nota_fiscal)
            print("Isto é o link da nota fiscal bruto: ", nota_fiscal_bruto)

            if data_do_pedido:
                try:
                    data_do_pedido = datetime.strptime(data_do_pedido, "%m/%d/%Y")
                    dias_passados = (datetime.today() - data_do_pedido).days + 1
                except ValueError:
                    dias_passados = "Data inválida"
            else:
                dias_passados = "Data não fornecida"

            results.append({
                # Informações padrão do pedido
                "ID": card_id,
                "Etiquetas": card_labels,
                "Título": card_title,
                "Fase": phase_name,
                "Tipo de envio": card_fields_data.get("entrega_via_correios_ou_ser_o_retirados_na_amlabs", ""),
                "Tempo na fase atual": tempo_na_fase,
                "Dias": dias_passados,
                "Setor": "ADMINISTRATIVO",
                "Pipe": "E01",
                "Responsavel": "",
                "Exceção": card_fields_data.get("pedido_c_exce_o", ""),
                "Nota fiscal": nota_fiscal,
                "Etiqueta dos Correios": etiqueta_dos_correios,
                "Responsavel do pedido": card_fields_data.get("responsible_card", ""),
                # Quantidades de itens
                "Kits Nano Market": safe_int(card_fields_data.get("quantos_kits_nano_market_deseja_1", "0")),
                "Nano Market Completo": safe_int(card_fields_data.get("nano_market_completo", "0")),
                "Quantidade de Kits Completo Trava de Geladeira": safe_int(card_fields_data.get("quantidade_de_kit_completo_trava_de_geladeira", "0")),
                "Quantidade de Kits Nano Market Completo": safe_int(card_fields_data.get("quantos_kits_nano_market_completo", "0")),
                "Quantidade de Travas Mecânicas": safe_int(card_fields_data.get("quantas_travas_mec_nicas_para_geladeira_voc_deseja", "0")),
                "Quantidade de Adaptadores": safe_int(card_fields_data.get("quantidade_de_adaptadores", "0")),
                "Quantidade de Adaptadores Micro Market": safe_int(card_fields_data.get("quantidade_de_adaptadores_micro_market_troca", "0")),
                "Quantidade de Módulo Controle de Acesso Geladeira Individual": safe_int(card_fields_data.get("quantidade_de_m_dulo_controle_de_acesso_geladeira_individual", "0")),
                "Quantidade de Módulo de Trava de Geladeira 4 Vias": safe_int(card_fields_data.get("quantidade_de_m_dulo_de_trava_de_at_4_geladeiras_troca", "0")),
                "Quantidade de Moderninha Smart": safe_int(card_fields_data.get("quantidade_de_moderninha_smart_troca", "0")),
                "Quantidade de Eletroim": safe_int(card_fields_data.get("quantidade_de_eletroim", "0")),
            })

    return results

def update_status(card_id, new_status):
    mutation = f"""
    mutation {{
        updateCardField(input: {{
            card_id: "{card_id}",
            field_id: "status_da_nota",
            new_value: "{new_status}"
        }}) {{
            card {{
                id
            }}
        }}
    }}
    """
    response = pipefy_send(mutation)
    return response

@app.route('/')
def home():
    return "Bem-vindo à API Pipefy!"

@app.route('/query_E02', methods=['GET'])
def query_e02_endpoint():
    result = query_E02()
    return jsonify(result)

@app.route('/update_action', methods=['POST'])
def update_action():
    data = request.json
    print(f"Recebido: {data}")  # Log para depuração
    card_id = data.get('card_id')
    new_value = data.get('new_value')
    
    # ID do campo que você quer atualizar no Pipefy
    field_id = 'responsible_card'
    
    # Chama a função de mutação
    mutation_card(card_id, field_id, new_value)
    
    return jsonify({'success': True})

@app.route('/histograma', methods=['GET'])
def tabela_view():
    dados = query_E02() + query_Trocas() + query_E01()
    campos = [
        "quantos_kits_nano_market_deseja_1",
    ]
    return render_template('histograma.html', dados=dados, campos=campos)

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
