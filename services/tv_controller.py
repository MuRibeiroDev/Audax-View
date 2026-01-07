"""
Controlador de TVs
Gerencia operações de controle e execução de sequências
"""

import threading
import time
from typing import Optional
from controllers import SmartThingsTV
from controllers.tv_control import pressionar_enter
from utils import log
from .webhook_service import WebhookService
from .sequence_mapper import SequenceMapper
import config


class TVController:
    """Controla operações de TVs (ligar, desligar, sequências)"""
    
    # Controle de sequências em execução (compartilhado entre instâncias)
    _sequencias_em_execucao = set()
    _sequencias_lock = threading.Lock()
    
    def __init__(self, tv_service, webhook_service: Optional[WebhookService] = None):
        self.tv_service = tv_service
        self.webhook_service = webhook_service or WebhookService()
        self.sequence_mapper = SequenceMapper()
    
    @classmethod
    def esta_executando_sequencia(cls, tv_nome: str) -> bool:
        """Verifica se uma TV está executando sequência no momento"""
        with cls._sequencias_lock:
            return tv_nome in cls._sequencias_em_execucao
    
    @classmethod
    def alguma_sequencia_em_execucao(cls) -> bool:
        """Verifica se há alguma sequência em execução"""
        with cls._sequencias_lock:
            return len(cls._sequencias_em_execucao) > 0
    
    @classmethod
    def _marcar_inicio_sequencia(cls, tv_nome: str):
        """Marca que uma sequência iniciou para uma TV"""
        with cls._sequencias_lock:
            cls._sequencias_em_execucao.add(tv_nome)
            log(f"[{tv_nome}] Sequência marcada como EM EXECUÇÃO", "INFO")
    
    @classmethod
    def _marcar_fim_sequencia(cls, tv_nome: str):
        """Marca que uma sequência finalizou para uma TV"""
        with cls._sequencias_lock:
            cls._sequencias_em_execucao.discard(tv_nome)
            log(f"[{tv_nome}] Sequência marcada como FINALIZADA", "INFO")
    
    def toggle_tv(self, tv_nome: str) -> bool:
        """
        Toggle de uma TV: se ligada desliga, se desligada liga + executa sequência
        """
        if not self.tv_service.tv_existe(tv_nome):
            log(f"[{tv_nome}] TV não encontrada", "ERROR")
            return False
        
        try:
            # Marca início da sequência
            self._marcar_inicio_sequencia(tv_nome)
            
            tv = SmartThingsTV(config.ACCESS_TOKEN)
            tv_info = self.tv_service.obter_tv(tv_nome)
            tv_id = tv_info["id"] if isinstance(tv_info, dict) else tv_info
            
            # Verifica status atual
            status_data = tv.obter_status(tv_id)
            is_on = False
            
            if status_data:
                try:
                    switch_value = status_data['components']['main']['switch']['switch']['value']
                    is_on = (switch_value == 'on')
                except (KeyError, TypeError):
                    pass
            
            # Toggle
            if is_on:
                log(f"[{tv_nome}] Desligando TV...", "INFO")
                tv._executar_comando_com_retry(tv_id, "switch", "off", max_tentativas=3, delay_retry=[10, 15])
            else:
                log(f"[{tv_nome}] TV está DESLIGADA - executando sequência mesmo assim", "WARNING")
                # Executa sequência mesmo com TV desligada
                self.sequence_mapper.executar_sequencia(tv, tv_id, tv_nome)
            
            return True
        except Exception as e:
            log(f"[{tv_nome}] Erro no toggle: {e}", "ERROR")
            return False
        finally:
            # Marca fim da sequência (sempre executa, mesmo com erro)
            self._marcar_fim_sequencia(tv_nome)
    
    def ligar_tv(self, tv_nome: str, enviar_webhook: bool = True) -> bool:
        """
        Liga uma TV específica (força ligar, não faz toggle)
        
        Args:
            tv_nome: Nome da TV
            enviar_webhook: Se True, envia webhook para ligar BI. Se False, apenas liga a TV
        """
        if not self.tv_service.tv_existe(tv_nome):
            log(f"[{tv_nome}] TV não encontrada", "ERROR")
            return False
        
        try:
            # Marca início da sequência
            self._marcar_inicio_sequencia(tv_nome)
            
            tv = SmartThingsTV(config.ACCESS_TOKEN)
            tv_info = self.tv_service.obter_tv(tv_nome)
            tv_id = tv_info["id"] if isinstance(tv_info, dict) else tv_info
            
            log(f"[{tv_nome}] Iniciando processo de ligar TV...", "INFO")
            
            # Envia webhook para ligar máquina virtual (apenas se solicitado)
            if enviar_webhook:
                self.webhook_service.enviar_comando_ligar(tv_nome)
            else:
                log(f"[{tv_nome}] Webhook ignorado (BI já está ligado)", "INFO")
            
            # Verifica se a TV está ligada antes de executar a sequência
            log(f"[{tv_nome}] Verificando status antes de executar sequência...", "INFO")
            status_data = tv.obter_status(tv_id)
            is_on = False
            
            if status_data:
                try:
                    switch_value = status_data['components']['main']['switch']['switch']['value']
                    is_on = (switch_value == 'on')
                except (KeyError, TypeError):
                    pass
            
            if not is_on:
                log(f"[{tv_nome}] TV está DESLIGADA - executando sequência mesmo assim", "WARNING")
            
            # Executa sequência de inicialização independente do estado da TV
            self.sequence_mapper.executar_sequencia(tv, tv_id, tv_nome)
            
            return True
        except Exception as e:
            log(f"[{tv_nome}] Erro ao ligar: {e}", "ERROR")
            return False
        finally:
            # Marca fim da sequência (sempre executa, mesmo com erro)
            self._marcar_fim_sequencia(tv_nome)
    
    def reconectar_tv(self, tv_nome: str) -> bool:
        """Executa sequência de reconexão: Enter -> Wait 10s -> Enter"""
        if not self.tv_service.tv_existe(tv_nome):
            log(f"[{tv_nome}] TV não encontrada", "ERROR")
            return False
        
        try:
            tv = SmartThingsTV(config.ACCESS_TOKEN)
            tv_info = self.tv_service.obter_tv(tv_nome)
            tv_id = tv_info["id"] if isinstance(tv_info, dict) else tv_info
            
            log(f"[{tv_nome}] Iniciando reconexão (Enter + 10s + Enter)...", "INFO")
            pressionar_enter(tv, tv_id, tv_nome, delay=10)
            pressionar_enter(tv, tv_id, tv_nome, delay=0)
            log(f"[{tv_nome}] Reconexão finalizada!", "SUCCESS")
            
            return True
        except Exception as e:
            log(f"[{tv_nome}] Erro na reconexão: {e}", "ERROR")
            return False
    
    def desligar_tvs_exceto_reuniao(self) -> dict:
        """
        Desliga todas as TVs exceto as de reunião, 2 por vez com intervalo de 10 segundos.
        
        Returns:
            dict: Relatório com TVs desligadas, ignoradas e erros
        """
        log("="*80, "INFO")
        log("🔌 INICIANDO DESLIGAMENTO EM LOTE (exceto reuniões)", "INFO")
        log("="*80, "INFO")
        
        # Filtra TVs excluindo as de reunião
        tvs_para_desligar = []
        tvs_ignoradas = []
        
        for nome_tv, info in self.tv_service.obter_tvs().items():
            setor = info.get('setor', '').lower()
            if setor in ['reunião', 'reuniao']:
                tvs_ignoradas.append(nome_tv)
                log(f"⏭️  [{nome_tv}] Ignorada (setor: {info.get('setor')})", "WARNING")
            else:
                tvs_para_desligar.append(nome_tv)
        
        log(f"\n📊 Total de TVs: {len(tvs_para_desligar) + len(tvs_ignoradas)}", "INFO")
        log(f"🔴 TVs para desligar: {len(tvs_para_desligar)}", "INFO")
        log(f"⏭️  TVs ignoradas (reunião): {len(tvs_ignoradas)}", "INFO")
        log("", "INFO")
        
        # Desliga 2 TVs por vez
        tvs_desligadas = []
        tvs_com_erro = []
        
        from controllers.tv_control import desligar_tv
        
        for i in range(0, len(tvs_para_desligar), 2):
            batch = tvs_para_desligar[i:i+2]
            threads = []
            
            log(f"\n🔄 Lote {i//2 + 1}/{(len(tvs_para_desligar) + 1)//2}", "INFO")
            log("-" * 60, "INFO")
            
            for nome_tv in batch:
                tv_info = self.tv_service.obter_tv(nome_tv)
                tv_id = tv_info["id"] if isinstance(tv_info, dict) else tv_info
                
                def desligar_thread(nome, tv_id):
                    try:
                        tv = SmartThingsTV(config.ACCESS_TOKEN)
                        desligar_tv(tv, tv_id, nome, delay=1)
                        tvs_desligadas.append(nome)
                        log(f"✅ [{nome}] Desligada com sucesso", "SUCCESS")
                    except Exception as e:
                        tvs_com_erro.append(nome)
                        log(f"❌ [{nome}] Erro ao desligar: {e}", "ERROR")
                
                thread = threading.Thread(target=desligar_thread, args=(nome_tv, tv_id))
                thread.daemon = True
                threads.append(thread)
                thread.start()
            
            # Aguarda threads terminarem
            for thread in threads:
                thread.join()
            
            # Intervalo de 10 segundos entre lotes (exceto no último)
            if i + 2 < len(tvs_para_desligar):
                log("\n⏱️  Aguardando 10 segundos antes do próximo lote...", "INFO")
                time.sleep(10)
        
        # Relatório final
        log("\n" + "="*80, "INFO")
        log("📊 RELATÓRIO FINAL", "INFO")
        log("="*80, "INFO")
        log(f"✅ TVs desligadas com sucesso: {len(tvs_desligadas)}", "SUCCESS")
        log(f"❌ TVs com erro: {len(tvs_com_erro)}", "ERROR")
        log(f"⏭️  TVs ignoradas (reunião): {len(tvs_ignoradas)}", "WARNING")
        log("="*80, "INFO")
        
        return {
            "success": True,
            "desligadas": tvs_desligadas,
            "ignoradas": tvs_ignoradas,
            "erros": tvs_com_erro,
            "total_desligadas": len(tvs_desligadas),
            "total_ignoradas": len(tvs_ignoradas),
            "total_erros": len(tvs_com_erro)
        }
    
    def toggle_todas(self, enviar_webhook: bool = True) -> bool:
        """
        Executa toggle em todas as TVs em blocos de 2 com execução intercalada e intervalo de 10s
        
        Args:
            enviar_webhook: Se True, envia webhook para ligar BIs. Se False, apenas liga TVs
        """
        def executar_todas():
            # Ordem específica das TVs (TVs de reunião por último)
            ordem_tvs = [
                "Operação 1 - TV1", "Operação 2 - TV2",
                "TV 1 Painel - TV3", "TV 2 Painel - TV4",
                "TV 3 Painel - TV5", "TV 4 Painel - TV6",
                "GESTÃO-INDUSTRIA", "ANTIFRAUDE",
                "CONTROLADORIA", "FINANCEIRO",
                "COBRANÇA", "TV-JURIDICO",
                "TVCADASTRO", "TI01",
                "TI02", "TI03"
            ]
            
            # Adiciona TVs de reunião no final
            tvs_disponiveis = self.tv_service.obter_tvs()
            tvs_reuniao = [nome for nome in tvs_disponiveis.keys() 
                          if "REUNIÃO" in nome.upper() or "REUNIAO" in nome.upper() 
                          or nome in ["TV-ATLAS", "TV-DIA D", "TV-MOSSAD", "TV-GEO-FOREST"]]
            
            # Filtra apenas TVs que existem no sistema
            tvs_ordenadas = [tv for tv in ordem_tvs if tv in tvs_disponiveis]
            tvs_ordenadas.extend(tvs_reuniao)
            
            total_tvs = len(tvs_ordenadas)
            
            if enviar_webhook:
                log(f"Iniciando toggle de {total_tvs} TVs em blocos de 2 INTERCALADOS (COM webhook para BIs)...", "INFO")
            else:
                log(f"Iniciando toggle de {total_tvs} TVs em blocos de 2 INTERCALADOS (SEM webhook - BIs já ligados)...", "INFO")
            
            # Processa em blocos de 2 com execução intercalada
            for i in range(0, total_tvs, 2):
                bloco = tvs_ordenadas[i:i+2]
                bloco_num = (i // 2) + 1
                
                log(f"[BLOCO {bloco_num}] Processando TVs INTERCALADAS: {', '.join(bloco)}", "INFO")
                
                if len(bloco) == 2:
                    # Execução intercalada: TV1 comando -> 10s -> TV2 comando -> 10s -> TV1 próximo -> ...
                    tv1, tv2 = bloco[0], bloco[1]
                    
                    # Inicia threads para ambas as TVs
                    thread1 = threading.Thread(target=self._toggle_tv_interno, args=(tv1, enviar_webhook))
                    thread2 = threading.Thread(target=self._toggle_tv_interno, args=(tv2, enviar_webhook))
                    
                    thread1.start()
                    log(f"[BLOCO {bloco_num}] {tv1} iniciada, aguardando 10s...", "INFO")
                    time.sleep(10)
                    
                    thread2.start()
                    log(f"[BLOCO {bloco_num}] {tv2} iniciada, aguardando 10s...", "INFO")
                    time.sleep(10)
                    
                    # Aguarda ambas finalizarem
                    thread1.join()
                    thread2.join()
                else:
                    # Apenas 1 TV no bloco (última TV ímpar)
                    thread = threading.Thread(target=self._toggle_tv_interno, args=(bloco[0], enviar_webhook))
                    thread.start()
                    thread.join()
                
                log(f"[BLOCO {bloco_num}] Concluído!", "SUCCESS")
            
            log("Todas as sequências finalizadas!", "SUCCESS")
        
        thread = threading.Thread(target=executar_todas)
        thread.daemon = True
        thread.start()
        return True
    
    def _toggle_tv_interno(self, tv_nome: str, enviar_webhook: bool) -> bool:
        """Método interno para toggle com controle de webhook"""
        if not self.tv_service.tv_existe(tv_nome):
            log(f"[{tv_nome}] TV não encontrada", "ERROR")
            return False
        
        try:
            # Marca início da sequência
            self._marcar_inicio_sequencia(tv_nome)
            
            tv = SmartThingsTV(config.ACCESS_TOKEN)
            tv_info = self.tv_service.obter_tv(tv_nome)
            tv_id = tv_info["id"] if isinstance(tv_info, dict) else tv_info
            
            # Verifica status atual
            status_data = tv.obter_status(tv_id)
            is_on = False
            
            if status_data:
                try:
                    switch_value = status_data['components']['main']['switch']['switch']['value']
                    is_on = (switch_value == 'on')
                except (KeyError, TypeError):
                    pass
            
            # Toggle
            if is_on:
                log(f"[{tv_nome}] Desligando TV...", "INFO")
                tv._executar_comando_com_retry(tv_id, "switch", "off", max_tentativas=3, delay_retry=[10, 15])
            else:
                log(f"[{tv_nome}] TV está DESLIGADA - executando sequência mesmo assim", "WARNING")
                # Executa sequência mesmo com TV desligada
                self.sequence_mapper.executar_sequencia(tv, tv_id, tv_nome)
            
            return True
        except Exception as e:
            log(f"[{tv_nome}] Erro no toggle: {e}", "ERROR")
            return False
        finally:
            # Marca fim da sequência (sempre executa, mesmo com erro)
            self._marcar_fim_sequencia(tv_nome)
