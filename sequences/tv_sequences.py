"""
Sequências de automação para cada TV
"""

from utils.logger import log
from controllers.tv_control import (
    ligar_tv,
    pressionar_home,
    pressionar_enter,
    pressionar_cima,
    pressionar_baixo,
    pressionar_esquerda,
    pressionar_direita
)


def sequencia_ti(tv, tv_id, nome_tv):
    """Sequência para TVs TI01, TI02 e TI03"""
    try:
        log(f"[{nome_tv}] Iniciando sequência...")
        ligar_tv(tv, tv_id, nome_tv, delay=3)
        pressionar_esquerda(tv, tv_id, nome_tv)
        pressionar_cima(tv, tv_id, nome_tv)
        pressionar_cima(tv, tv_id, nome_tv)
        pressionar_enter(tv, tv_id, nome_tv)
        pressionar_baixo(tv, tv_id, nome_tv)
        pressionar_enter(tv, tv_id, nome_tv)
        pressionar_enter(tv, tv_id, nome_tv, delay=0)
        log(f"[{nome_tv}] Sequência finalizada!", "SUCCESS")
        return True
    except Exception as e:
        log(f"[{nome_tv}] ERRO: {e}", "ERROR")
        return False


def sequencia_atlas(tv, tv_id):
    """Sequência para TV-ATLAS"""
    try:
        log("[TV-ATLAS] Iniciando sequência...")
        ligar_tv(tv, tv_id, "TV-ATLAS", delay=5)
        pressionar_home(tv, tv_id, "TV-ATLAS")
        pressionar_esquerda(tv, tv_id, "TV-ATLAS")
        pressionar_baixo(tv, tv_id, "TV-ATLAS")
        pressionar_direita(tv, tv_id, "TV-ATLAS")
        pressionar_direita(tv, tv_id, "TV-ATLAS")
        pressionar_direita(tv, tv_id, "TV-ATLAS")
        pressionar_enter(tv, tv_id, "TV-ATLAS")
        pressionar_direita(tv, tv_id, "TV-ATLAS")
        pressionar_enter(tv, tv_id, "TV-ATLAS", delay=0)
        log("[TV-ATLAS] Sequência finalizada!", "SUCCESS")
        return True
    except Exception as e:
        log(f"[TV-ATLAS] ERRO: {e}", "ERROR")
        return False


def sequencia_juridico(tv, tv_id):
    """Sequência para TV-JURIDICO"""
    try:
        log("[TV-JURIDICO] Iniciando sequência...")
        ligar_tv(tv, tv_id, "TV-JURIDICO", delay=15)
        pressionar_enter(tv, tv_id, "TV-JURIDICO", delay=6)
        pressionar_direita(tv, tv_id, "TV-JURIDICO", delay=5)
        pressionar_direita(tv, tv_id, "TV-JURIDICO", delay=5)
        pressionar_enter(tv, tv_id, "TV-JURIDICO", delay=6)
        pressionar_baixo(tv, tv_id, "TV-JURIDICO", delay=5)
        pressionar_baixo(tv, tv_id, "TV-JURIDICO", delay=5)
        pressionar_baixo(tv, tv_id, "TV-JURIDICO", delay=5)
        pressionar_direita(tv, tv_id, "TV-JURIDICO", delay=5)
        pressionar_baixo(tv, tv_id, "TV-JURIDICO", delay=5)
        pressionar_baixo(tv, tv_id, "TV-JURIDICO", delay=5)
        pressionar_enter(tv, tv_id, "TV-JURIDICO", delay=5)
        pressionar_direita(tv, tv_id, "TV-JURIDICO", delay=5)
        pressionar_enter(tv, tv_id, "TV-JURIDICO", delay=5)
        pressionar_baixo(tv, tv_id, "TV-JURIDICO", delay=5)
        pressionar_baixo(tv, tv_id, "TV-JURIDICO", delay=5)
        pressionar_baixo(tv, tv_id, "TV-JURIDICO", delay=5)
        pressionar_cima(tv, tv_id, "TV-JURIDICO", delay=10)
        pressionar_cima(tv, tv_id, "TV-JURIDICO", delay=10)
        pressionar_enter(tv, tv_id, "TV-JURIDICO")
        log("[TV-JURIDICO] Sequência finalizada!", "SUCCESS")
        return True
    except Exception as e:
        log(f"[TV-JURIDICO] ERRO: {e}", "ERROR")
        return False


def sequencia_operacao1_tv1(tv, tv_id):
    """Sequência para OPERAÇÃO-1---TV1"""
    nome = "OPERAÇÃO-1---TV1"
    try:
        log(f"[{nome}] Iniciando sequência...")
        ligar_tv(tv, tv_id, nome)
        pressionar_home(tv, tv_id, nome)
        for i in range(6):
            pressionar_direita(tv, tv_id, nome, delay=5)
        pressionar_enter(tv, tv_id, nome, delay=10)
        pressionar_baixo(tv, tv_id, nome, delay=5)
        pressionar_baixo(tv, tv_id, nome, delay=5)
        pressionar_cima(tv, tv_id, nome, delay=10)
        pressionar_enter(tv, tv_id, nome, delay=15)
        pressionar_enter(tv, tv_id, nome, delay=0)
        log(f"[{nome}] Sequência finalizada!", "SUCCESS")
        return True
    except Exception as e:
        log(f"[{nome}] ERRO: {e}", "ERROR")
        return False


def sequencia_operacao2_tv2(tv, tv_id):
    """Sequência para OPERAÇÃO-2---TV2"""
    nome = "OPERAÇÃO-2---TV2"
    try:
        log(f"[{nome}] Iniciando sequência...")
        ligar_tv(tv, tv_id, nome)
        pressionar_home(tv, tv_id, nome)
        for i in range(10):
            pressionar_direita(tv, tv_id, nome, delay=2)
        pressionar_enter(tv, tv_id, nome, delay=10)
        for i in range(3):
            pressionar_baixo(tv, tv_id, nome, delay=2)
        pressionar_cima(tv, tv_id, nome)
        pressionar_enter(tv, tv_id, nome, delay=15)
        pressionar_enter(tv, tv_id, nome, delay=0)
        log(f"[{nome}] Sequência finalizada!", "SUCCESS")
        return True
    except Exception as e:
        log(f"[{nome}] ERRO: {e}", "ERROR")
        return False


def sequencia_tv1_painel_tv3(tv, tv_id):
    """Sequência para TV-1-PAINEL---TV3"""
    nome = "TV-1-PAINEL---TV3"
    try:
        log(f"[{nome}] Iniciando sequência...")
        ligar_tv(tv, tv_id, nome)
        pressionar_home(tv, tv_id, nome)
        for i in range(3):
            pressionar_esquerda(tv, tv_id, nome, delay=2)
        pressionar_cima(tv, tv_id, nome, delay=2)
        pressionar_direita(tv, tv_id, nome, delay=2)
        pressionar_direita(tv, tv_id, nome, delay=3)
        pressionar_enter(tv, tv_id, nome, delay=10)
        pressionar_baixo(tv, tv_id, nome, delay=2)
        pressionar_baixo(tv, tv_id, nome, delay=2)
        pressionar_cima(tv, tv_id, nome)
        pressionar_enter(tv, tv_id, nome, delay=15)
        pressionar_enter(tv, tv_id, nome, delay=0)
        log(f"[{nome}] Sequência finalizada!", "SUCCESS")
        return True
    except Exception as e:
        log(f"[{nome}] ERRO: {e}", "ERROR")
        return False
