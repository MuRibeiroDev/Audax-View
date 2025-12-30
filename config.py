"""
Configurações do sistema de controle de TVs Samsung
"""

# Token de acesso SmartThings
ACCESS_TOKEN = "04380ff9-0feb-45a2-b0ae-d2580bf80455"

# AVISO: Se você está recebendo erros 401, o token pode ter expirado.
# Para gerar um novo token:
# 1. Acesse: https://account.smartthings.com/tokens
# 2. Crie um novo Personal Access Token
# 3. Marque as permissões: devices (read, write, execute)
# 4. Substitua o ACCESS_TOKEN acima pelo novo token gerado

# IDs das TVs
TVS = {
    "OPERAÇÃO-2---TV2": "a856316a-8b57-f399-e72b-fd595c67edd3",
    "TV-ATLAS": "65a53ea8-334d-1510-94c0-915fbbd2ceb1",
    "TV-1-PAINEL---TV3": "541381f7-f709-60f1-312e-4157dd324528",
    "TV-JURIDICO": "d339553c-5dc4-e28d-e0f2-e188e81b0fca",
    "OPERAÇÃO-1---TV1": "4321bd17-6f06-cdfc-08ac-8edef0b768ae",
    "TI01": "98c6e6f8-95b4-cebd-58c3-89b0c8914c98",
    "TI02": "b836e65f-4c6f-0019-ae1b-26dc4f08f634",
    "TI03": "9aec8b23-27bd-cbf5-ed28-36ae181bf20d"
}

# URL do webhook para ligar máquinas virtuais
WEBHOOK_URL = "http://172.16.30.10:5679/webhook-test/ligatvsmurilo"

# Configurações do servidor
HOST = '0.0.0.0'
PORT = 5000
DEBUG = True

# Configurações de renovação automática de token
TOKEN_AUTO_RENOVACAO = True  # True para ativar, False para desativar
TOKEN_HORARIO_RENOVACAO = "10:29"  # Horário diário para renovar (formato HH:MM)
