# Sistema de Controle de TVs Samsung - Instruções para Agentes de IA

## Estilo de Comunicação

**Objetivo**: Reduzir consumo de tokens mantendo precisão técnica.

**Regras de Resposta**:
- Priorize respostas curtas e objetivas
- Forneça apenas o essencial: trechos mínimos de código, explicações com no máximo 3 frases, listas curtas
- Não repita partes já fornecidas da conversa
- Em caso de ambiguidade, faça uma única pergunta direta
- Evite teoria extensa e comentários redundantes
- Use placeholders quando o contexto completo não for necessário
- Em código: remova comentários desnecessários, evite duplicação, não inclua imports ou boilerplate não essenciais
- Se faltar informação, diga isso de forma concisa
- Mantenha foco no problema técnico imediato

## Arquitetura Geral

Este é um sistema Flask para controlar TVs Samsung via SmartThings API, com integração WhatsApp (Evolution API) e automação de sequências. A arquitetura segue padrões de **camadas de serviço** com injeção de dependência.

### Estrutura de Camadas

```
routes/ (Apresentação) → services/ (Lógica de Negócio) → controllers/ (API Externa)
                              ↓
                         config.py (Configurações)
```

- **routes/**: Endpoints HTTP, validação de entrada, delegação para services
- **services/**: Toda lógica de negócio (TVService, TVController, WebhookService, SchedulerService, WhatsAppService)
- **controllers/**: Cliente SmartThings API e funções de controle remoto
- **sequences/**: Sequências de automação específicas por TV
- **utils/**: Logger e renovador de token automático

## Padrões Críticos do Projeto

### 1. Controle de Sequências em Execução (Thread-Safe)

**IMPORTANTE**: O sistema rastreia sequências em execução para evitar interferência do keep-alive:

```python
# Em TVController - variáveis de classe compartilhadas
_sequencias_em_execucao = set()  # TVs executando sequências
_sequencias_lock = threading.Lock()  # Thread safety

# SEMPRE usar try/finally para marcar início e fim
def ligar_tv(self, tv_nome: str):
    try:
        self._marcar_inicio_sequencia(tv_nome)
        # ... executa sequência
    finally:
        self._marcar_fim_sequencia(tv_nome)
```

**Razão**: Keep-alive executa "Enter + 10s + Enter" a cada 5min. Se executar durante fluxo inicial, adiciona comandos extras que bugam a sequência.

### 2. Execução em Threads e Blocos

Operações de múltiplas TVs usam threads com execução **intercalada em blocos de 2**:

```python
# Padrão para toggle_todas():
# Bloco 1: TV1 inicia → 10s → TV2 inicia → 10s
# Aguarda ambas finalizarem (thread.join())
# Bloco 2: TV3 inicia → 10s → TV4 inicia → ...
```

**Razão**: Evita sobrecarga da API e permite execução paralela controlada.

### 3. Webhooks para Máquinas Virtuais

TVs dependem de máquinas virtuais (BIs) que precisam ser ligadas primeiro:

- `enviar_webhook=True` → Liga BI + TV (primeira vez)
- `enviar_webhook=False` → Apenas TV (BIs já ligados)

Mapeamento em `services/webhook_service.py` → `TV_WEBHOOK_MAP`

### 4. Sequências de Automação

Cada TV tem sequência específica de navegação no menu:
- Mapeadas em `services/sequence_mapper.py` → método `executar_sequencia()`
- Implementadas em `sequences/tv_sequences.py`
- Usam funções de `controllers/tv_control.py` (ligar_tv, pressionar_enter, etc)

**Padrão comum**:
```python
def sequencia_<nome>(tv, tv_id):
    try:
        log(f"[{nome}] Iniciando sequência...")
        ligar_tv(tv, tv_id, nome, delay=15)
        pressionar_enter(tv, tv_id, nome, delay=6)
        # ... comandos específicos
        log(f"[{nome}] Sequência finalizada!", "SUCCESS")
        return True
    except Exception as e:
        log(f"[{nome}] ERRO: {e}", "ERROR")
        return False
```

### 5. Sistema de Logs Centralizado

```python
from utils import log

log("mensagem", "INFO")    # Padrão
log("sucesso", "SUCCESS")  # Verde
log("alerta", "WARNING")   # Amarelo
log("erro", "ERROR")       # Vermelho
```

Logs armazenados em `deque` (últimos 500) e exibidos na interface web.

### 6. Keep-Alive e Scheduler

- **Keep-Alive**: Executa `Enter + 10s + Enter` em TVs ligadas a cada X minutos
- **Verifica**: `TVController.alguma_sequencia_em_execucao()` antes de executar
- **Ignora**: TVs com "REUNIÃO" no nome e setores em `KEEP_ALIVE_IGNORE_SETORES`
- **Renovação Token**: Automática via Selenium, horário configurável

## Comandos Essenciais

```bash
# Executar aplicação
python app.py

# Instalar dependências
pip install -r requirements.txt

# Estrutura Docker (Evolution API)
docker-compose up -d
```

## Convenções de Código

1. **Services recebem dependências via construtor** (injeção de dependência):
   ```python
   tv_controller = TVController(tv_service, webhook_service)
   ```

2. **Métodos de classe para estado compartilhado** (ex: `_sequencias_em_execucao`)

3. **Factory pattern** em `create_app()` para configurar aplicação

4. **Threads daemon** para operações longas:
   ```python
   thread = threading.Thread(target=executar_todas)
   thread.daemon = True
   thread.start()
   ```

5. **Retry pattern** nos comandos SmartThings:
   ```python
   tv._executar_comando_com_retry(tv_id, comando, args, 
                                    max_tentativas=3, 
                                    delay_retry=[10, 15])
   ```

## Integrações Externas

### SmartThings API
- Token em `config.ACCESS_TOKEN`
- Cliente em `controllers/smartthings.py`
- IDs de TVs em `config.TV_CONFIG`

### Evolution API (WhatsApp)
- URL: `config.EVOLUTION_API_URL`
- Instância: `config.EVOLUTION_INSTANCE`
- Autorização: apenas `config.WHATSAPP_AUTORIZADO`
- Comandos: `!ligartvs`, `!religartvs`, `!ligar <nome>`, `!status`, `!listartvs`

### Webhook Virtual Machines
- URL: `config.WEBHOOK_URL`
- Formato: `[{"output": "[{\"tv\": \"X\", \"mode\": \"Turn on\"}]"}]`

## Fluxos de Dados Importantes

### Ligar todas as TVs:
```
WhatsApp → /webhook/whatsapp → processar_comando("!ligartvs")
  → TVController.toggle_todas(enviar_webhook=True)
  → WebhookService.enviar_comando_ligar() (por TV)
  → SequenceMapper.executar_sequencia() (por TV)
  → controllers/tv_control (comandos individuais)
```

### Keep-Alive:
```
SchedulerService.executar_keep_alive() (a cada 5min)
  → Verifica TVController.alguma_sequencia_em_execucao()
  → Se False: processa TVs em lotes de 2
  → Para cada TV ligada: pressionar_enter() x2 com delay
```

## Debugging

- Logs aparecem no terminal e na interface web (`/`)
- Status de TVs: endpoint `/api/tvs/status`
- Logs endpoint: `/api/logs`
- Verificar sequências em execução: `TVController._sequencias_em_execucao` (set)

## Considerações ao Modificar

- **Adicionar nova TV**: Atualizar `config.TV_CONFIG`, criar sequência em `sequences/tv_sequences.py`, mapear em `sequence_mapper.py`
- **Adicionar comando WhatsApp**: Modificar `routes/whatsapp_routes.py` → `processar_comando()`
- **Mudar keep-alive**: Alterar `config.KEEP_ALIVE_INTERVALO` ou `KEEP_ALIVE_IGNORE_SETORES`
- **Problemas de token**: Renovar em https://account.smartthings.com/tokens ou aguardar renovação automática

## Arquivos Críticos

- `config.py` - Todas configurações centralizadas (TOKEN, TVs, URLs)
- `services/tv_controller.py` - Controle de estado e sequências
- `services/scheduler_service.py` - Keep-alive e renovação token
- `sequences/tv_sequences.py` - Sequências de automação
- `ARCHITECTURE.md` - Documentação completa da arquitetura
