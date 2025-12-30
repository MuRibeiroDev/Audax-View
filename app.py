"""
Servidor Flask para controle das TVs Samsung via interface web
"""

import sys
import threading
import requests
import schedule
import time
import importlib
from pathlib import Path
from flask import Flask, jsonify, render_template, request

# Importações locais
import config
from config import TVS, WEBHOOK_URL, HOST, PORT, DEBUG, TOKEN_AUTO_RENOVACAO, TOKEN_HORARIO_RENOVACAO
from utils import log, LOGS, LOGS_LOCK
from controllers import SmartThingsTV
from utils.renovador_token import RenovadorTokenSmartThings
from sequences import (
    sequencia_ti,
    sequencia_atlas,
    sequencia_juridico,
    sequencia_operacao1_tv1,
    sequencia_operacao2_tv2,
    sequencia_tv1_painel_tv3
)

# Inicializa o Flask
app = Flask(__name__)

# Configuração do renovador de token
TOKEN_CONFIG_FILE = Path(__file__).parent / 'token_config.json'
renovador_token = RenovadorTokenSmartThings()
token_thread = None


# ========== ROTAS ==========

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')


@app.route('/api/tvs')
def listar_tvs():
    """Lista todas as TVs disponíveis"""
    return jsonify({
        "success": True,
        "tvs": list(TVS.keys())
    })


@app.route('/api/token/config', methods=['GET', 'POST'])
def config_token():
    """Configura horário de renovação do token"""
    import json
    from datetime import datetime
    
    if request.method == 'POST':
        data = request.get_json()
        horario = data.get('horario', '02:00')
        
        try:
            # Valida formato
            datetime.strptime(horario, "%H:%M")
            
            # Salva configuração
            config = {'horario': horario, 'ativo': True}
            with open(TOKEN_CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            
            # Reinicia agendamento
            iniciar_renovacao_token(horario)
            
            log(f"[TOKEN] Renovação agendada para {horario}", "SUCCESS")
            return jsonify({
                "success": True,
                "message": f"Renovação agendada para {horario}"
            })
        except ValueError:
            return jsonify({
                "success": False,
                "message": "Horário inválido! Use formato HH:MM"
            }), 400
    
    # GET: retorna configuração atual
    try:
        import json
        if TOKEN_CONFIG_FILE.exists():
            with open(TOKEN_CONFIG_FILE, 'r') as f:
                config = json.load(f)
        else:
            config = {'horario': '02:00', 'ativo': False}
        return jsonify({"success": True, "config": config})
    except:
        return jsonify({"success": True, "config": {'horario': '02:00', 'ativo': False}})


@app.route('/api/token/renovar', methods=['POST'])
def renovar_token_manual():
    """Executa renovação manual do token"""
    def executar():
        try:
            log("[TOKEN] Iniciando renovação manual...", "INFO")
            resultado = renovador_token.renovar()
            if resultado:
                # Recarrega o módulo config para pegar o novo token
                importlib.reload(config)
                log("[TOKEN] Renovação concluída e configuração recarregada!", "SUCCESS")
                log(f"[TOKEN] Novo token ativo: {config.ACCESS_TOKEN[:20]}...", "INFO")
            else:
                log("[TOKEN] Erro na renovação", "ERROR")
        except Exception as e:
            log(f"[TOKEN] Erro: {e}", "ERROR")
    
    thread = threading.Thread(target=executar)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Renovação iniciada em segundo plano"
    })


@app.route('/api/executar/<tv_nome>', methods=['GET', 'POST'])
def executar_sequencia(tv_nome):
    """Executa a sequência de uma TV específica (toggle power)"""
    if tv_nome not in TVS:
        return jsonify({
            "success": False,
            "sucesso": False,
            "message": f"TV {tv_nome} não encontrada",
            "mensagem": f"TV {tv_nome} não encontrada"
        }), 404
    
    def executar():
        # Usa o token atual do módulo config
        tv = SmartThingsTV(config.ACCESS_TOKEN)
        tv_id = TVS[tv_nome]
        
        # Verifica o status atual da TV
        status_data = tv.obter_status(tv_id)
        is_on = False
        
        if status_data:
            try:
                switch_value = status_data['components']['main']['switch']['switch']['value']
                is_on = (switch_value == 'on')
            except (KeyError, TypeError):
                pass
        
        # Toggle: se está ligada, desliga; se está desligada, executa sequência
        if is_on:
            log(f"[{tv_nome}] Desligando TV...")
            tv._executar_comando_com_retry(tv_id, "switch", "off", max_tentativas=3, delay_retry=[10, 15])
        else:
            # Envia webhook para ligar a máquina virtual
            log(f"[{tv_nome}] Enviando webhook para ligar máquina virtual...")
            try:
                webhook_data = {"tv": tv_nome}
                response = requests.post(WEBHOOK_URL, json=webhook_data, timeout=5)
                log(f"[{tv_nome}] Webhook enviado: {response.status_code}", "SUCCESS")
            except Exception as e:
                log(f"[{tv_nome}] Erro ao enviar webhook: {e}", "ERROR")
            
            # Executa a sequência específica para ligar e configurar
            if tv_nome in ["TI01", "TI02", "TI03"]:
                sequencia_ti(tv, tv_id, tv_nome)
            elif tv_nome == "TV-ATLAS":
                sequencia_atlas(tv, tv_id)
            elif tv_nome == "TV-JURIDICO":
                sequencia_juridico(tv, tv_id)
            elif tv_nome == "OPERAÇÃO-1---TV1":
                sequencia_operacao1_tv1(tv, tv_id)
            elif tv_nome == "OPERAÇÃO-2---TV2":
                sequencia_operacao2_tv2(tv, tv_id)
            elif tv_nome == "TV-1-PAINEL---TV3":
                sequencia_tv1_painel_tv3(tv, tv_id)
    
    # Executa em thread separada para não bloquear a resposta
    thread = threading.Thread(target=executar)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "sucesso": True,
        "message": f"Comando enviado para {tv_nome}",
        "mensagem": f"Comando enviado para {tv_nome}"
    })


@app.route('/api/executar/todas')
def executar_todas():
    """Executa a sequência de todas as TVs simultaneamente"""
    def executar_todas_threads():
        tv = SmartThingsTV(config.ACCESS_TOKEN)
        threads = []
        
        # TI01
        t1 = threading.Thread(target=sequencia_ti, args=(tv, TVS["TI01"], "TI01"))
        threads.append(t1)
        
        # TI02
        t2 = threading.Thread(target=sequencia_ti, args=(tv, TVS["TI02"], "TI02"))
        threads.append(t2)
        
        # TI03
        t3 = threading.Thread(target=sequencia_ti, args=(tv, TVS["TI03"], "TI03"))
        threads.append(t3)
        
        # TV-ATLAS
        t4 = threading.Thread(target=sequencia_atlas, args=(tv, TVS["TV-ATLAS"]))
        threads.append(t4)
        
        # TV-JURIDICO
        t5 = threading.Thread(target=sequencia_juridico, args=(tv, TVS["TV-JURIDICO"]))
        threads.append(t5)
        
        # Inicia todas as threads
        for t in threads:
            t.start()
        
        # Aguarda todas finalizarem
        for t in threads:
            t.join()
        
        log("Todas as sequências finalizadas!", "SUCCESS")
    
    # Executa em thread separada
    thread = threading.Thread(target=executar_todas_threads)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Sequências de todas as TVs iniciadas"
    })


@app.route('/api/logs')
def obter_logs():
    """Retorna os logs do sistema"""
    with LOGS_LOCK:
        logs_list = list(LOGS)
    
    return jsonify({
        "success": True,
        "logs": logs_list,
        "total": len(logs_list)
    })


@app.route('/api/logs/limpar', methods=['POST'])
def limpar_logs():
    """Limpa todos os logs"""
    with LOGS_LOCK:
        LOGS.clear()
    log("Logs limpos pelo usuário", "INFO")
    
    return jsonify({
        "success": True,
        "message": "Logs limpos com sucesso"
    })


@app.route('/api/status/<tv_nome>')
def obter_status_tv(tv_nome):
    """Obtém o status (ligada/desligada) de uma TV específica"""
    if tv_nome not in TVS:
        return jsonify({
            "success": False,
            "message": f"TV {tv_nome} não encontrada"
        }), 404
    
    tv = SmartThingsTV(config.ACCESS_TOKEN)
    tv_id = TVS[tv_nome]
    status_data = tv.obter_status(tv_id)
    
    is_on = False
    if status_data:
        try:
            switch_value = status_data['components']['main']['switch']['switch']['value']
            is_on = (switch_value == 'on')
        except (KeyError, TypeError):
            pass
            
    return jsonify({
        "success": True,
        "tv": tv_nome,
        "is_on": is_on
    })


@app.route('/api/status/todas')
def obter_status_todas():
    """Obtém o status de todas as TVs"""
    tv = SmartThingsTV(config.ACCESS_TOKEN)
    resultados = {}
    
    def check_status(nome, id):
        # Verifica status (ligada/desligada)
        status_data = tv.obter_status(id)
        is_on = False
        is_online = False
        current_app = None
        input_source = None
        volume = None
        
        if status_data:
            is_online = True  # Se conseguiu obter status, está online
            try:
                switch_value = status_data['components']['main']['switch']['switch']['value']
                is_on = (switch_value == 'on')
                log(f"[{nome}] Switch: {switch_value}, Ligada: {is_on}", "INFO")
            except (KeyError, TypeError) as e:
                log(f"[{nome}] Erro ao ler switch status: {e}", "ERROR")
            
            # App/Canal atual
            try:
                current_app = status_data['components']['main']['tvChannel']['tvChannelName']['value']
            except (KeyError, TypeError):
                pass
            
            # Entrada atual
            try:
                input_source = status_data['components']['main']['samsungvd.mediaInputSource']['inputSource']['value']
            except (KeyError, TypeError):
                pass
            
            # Volume
            try:
                volume = status_data['components']['main']['audioVolume']['volume']['value']
            except (KeyError, TypeError):
                pass
        else:
            log(f"[{nome}] Não foi possível obter status - TV offline", "WARNING")

        resultados[nome] = {
            "is_on": is_on,
            "is_online": is_online,
            "current_app": current_app,
            "input_source": input_source,
            "volume": volume
        }

    threads = []
    for nome, id in TVS.items():
        t = threading.Thread(target=check_status, args=(nome, id))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
        
    return jsonify({
        "success": True,
        "status": resultados
    })


# ========== FUNÇÕES DE RENOVAÇÃO DE TOKEN ==========

def iniciar_renovacao_token(horario='02:00'):
    """Inicia thread de renovação automática de token"""
    global token_thread
    
    # Cancela agendamentos anteriores
    schedule.clear()
    
    # Função de renovação com reload do config
    def renovar_e_recarregar():
        log("[TOKEN] Iniciando renovação automática...", "INFO")
        resultado = renovador_token.renovar()
        if resultado:
            # Recarrega o módulo config para pegar o novo token
            importlib.reload(config)
            log("[TOKEN] Token renovado e configuração recarregada!", "SUCCESS")
            log(f"[TOKEN] Novo token: {config.ACCESS_TOKEN[:20]}...", "INFO")
        else:
            log("[TOKEN] Falha na renovação automática", "ERROR")
        return resultado
    
    # Agenda nova renovação
    schedule.every().day.at(horario).do(renovar_e_recarregar)
    log(f"[TOKEN] Renovação agendada para {horario}", "SUCCESS")
    
    # Thread de agendamento
    def run_schedule():
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    if token_thread is None or not token_thread.is_alive():
        token_thread = threading.Thread(target=run_schedule, daemon=True)
        token_thread.start()


# ========== INICIALIZAÇÃO ==========

if __name__ == '__main__':
    import json
    sys.stdout.reconfigure(line_buffering=True)
    
    log("=== Sistema de Controle de TVs Samsung ===", "INFO")
    log("Iniciando servidor web na porta 5000...", "INFO")
    log("Acesse: http://localhost:5000", "INFO")
    log("Logs disponíveis em: http://localhost:5000/api/logs", "INFO")
    
    # Lista de TVs disponíveis
    print("\n" + "="*50)
    print("📺 TVS DISPONÍVEIS NA API:")
    print("="*50)
    for i, (nome, device_id) in enumerate(TVS.items(), 1):
        print(f"  {i}. {nome:<15} → {device_id}")
    print("="*50 + "\n")
    
    # Sistema de renovação automática de token
    if TOKEN_AUTO_RENOVACAO:
        try:
            iniciar_renovacao_token(TOKEN_HORARIO_RENOVACAO)
            log(f"[TOKEN] Sistema de renovação automática ativado ({TOKEN_HORARIO_RENOVACAO})", "SUCCESS")
        except Exception as e:
            log(f"[TOKEN] Erro ao iniciar renovação automática: {e}", "ERROR")
    else:
        log("[TOKEN] Renovação automática desativada (config.py)", "INFO")
    
    app.run(debug=DEBUG, host=HOST, port=PORT, use_reloader=False)
