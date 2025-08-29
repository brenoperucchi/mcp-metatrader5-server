"""
Cliente MCP base para comunicação com o servidor MetaTrader 5 MCP
"""

import asyncio
import logging
import time
import json
import os
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    
from .exceptions import (
    ConnectionError, TimeoutError, MCPError, RetryError,
    AuthenticationError, MT5ClientError
)
from .models import MCPResponse

# Configurar logging seguindo as regras do usuário
logger = logging.getLogger(__name__)


class MCPClient:
    """Cliente base para comunicação MCP assíncrona"""
    
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:50051",
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        log_dir: Optional[str] = None
    ):
        """
        Inicializa o cliente MCP
        
        Args:
            base_url: URL base do servidor MCP
            timeout: Timeout para requisições em segundos
            max_retries: Número máximo de tentativas de retry
            retry_delay: Delay entre tentativas de retry
            log_dir: Diretório para logs (seguindo regra logs/command_name/)
        """
        self.base_url = base_url.rstrip('/')
        self.mcp_url = f"{self.base_url}/mcp"
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Configurar logging estruturado
        self._setup_logging(log_dir)
        
        # Estado da conexão
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_id: Optional[str] = None
        self._request_id = 0
        self._connected = False
        
        # Estatísticas
        self._stats = {
            "requests_sent": 0,
            "requests_successful": 0,
            "requests_failed": 0,
            "total_latency_ms": 0.0,
            "avg_latency_ms": 0.0,
            "last_request_time": None
        }
    
    def _setup_logging(self, log_dir: Optional[str] = None):
        """Configurar logging seguindo regras do usuário"""
        if not log_dir:
            # Usar logs/mcp_client/ seguindo regra logs/command_name/
            log_dir = "logs/mcp_client"
        
        os.makedirs(log_dir, exist_ok=True)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"mcp_client_{timestamp}.log")
        
        # Configurar handler de arquivo se ainda não existe
        if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
            logger.addHandler(file_handler)
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.disconnect()
    
    async def connect(self):
        """Estabelecer conexão com o servidor MCP"""
        if not AIOHTTP_AVAILABLE:
            raise ConnectionError("aiohttp não está instalado. Execute: pip install aiohttp")
        
        if self._session:
            return
        
        try:
            # Configurar timeout e headers
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "User-Agent": "MT5-MCP-Client/1.0"
            }
            
            # Criar sessão
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
            
            # Testar conectividade
            await self._test_connection()
            
            self._connected = True
            logger.info(f"Conectado ao servidor MCP em {self.base_url}")
            
        except Exception as e:
            if self._session:
                await self._session.close()
                self._session = None
            raise ConnectionError(f"Falha ao conectar ao servidor MCP: {str(e)}")
    
    async def disconnect(self):
        """Encerrar conexão com o servidor MCP"""
        if self._session:
            await self._session.close()
            self._session = None
            self._session_id = None
            self._connected = False
            logger.info("Desconectado do servidor MCP")
    
    async def _test_connection(self):
        """Testar conectividade básica"""
        try:
            await self._make_request("tools/list")
            logger.debug("Teste de conectividade bem-sucedido")
        except Exception as e:
            raise ConnectionError(f"Teste de conectividade falhou: {str(e)}")
    
    def _next_request_id(self) -> str:
        """Gerar próximo ID de requisição"""
        self._request_id += 1
        return f"req_{self._request_id}_{int(time.time() * 1000)}"
    
    async def _make_request(
        self, 
        method: str, 
        params: Optional[Dict[str, Any]] = None,
        retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Fazer uma requisição MCP com retry logic
        
        Args:
            method: Método MCP a ser chamado
            params: Parâmetros da requisição
            retries: Número de tentativas (usa self.max_retries se None)
            
        Returns:
            Resposta da requisição
            
        Raises:
            ConnectionError: Problema de conexão
            MCPError: Erro do protocolo MCP
            TimeoutError: Timeout na requisição
            RetryError: Todas as tentativas falharam
        """
        if not self._session:
            await self.connect()
        
        if retries is None:
            retries = self.max_retries
        
        # Preparar requisição
        request_data = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": method
        }
        
        if params:
            request_data["params"] = params
        
        # Tentar requisição com retry
        last_error = None
        
        for attempt in range(retries + 1):
            try:
                start_time = time.perf_counter()
                
                # Log da tentativa
                if attempt > 0:
                    logger.warning(f"Tentativa {attempt + 1}/{retries + 1} para {method}")
                
                async with self._session.post(
                    self.mcp_url,
                    json=request_data
                ) as response:
                    
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    
                    # Atualizar estatísticas
                    self._update_stats(elapsed_ms, success=response.status == 200)
                    
                    # Verificar status HTTP
                    if response.status == 401:
                        raise AuthenticationError(f"Acesso negado: {await response.text()}")
                    elif response.status == 404:
                        raise ConnectionError(f"Servidor MCP não encontrado: {self.mcp_url}")
                    elif response.status != 200:
                        error_text = await response.text()
                        raise ConnectionError(f"HTTP {response.status}: {error_text}")
                    
                    # Processar resposta JSON
                    try:
                        result = await response.json()
                    except json.JSONDecodeError as e:
                        raise MCPError(f"Resposta não é JSON válido: {str(e)}")
                    
                    # Verificar erros MCP
                    if "error" in result:
                        error = result["error"]
                        error_code = error.get("code")
                        error_message = error.get("message", "Erro MCP desconhecido")
                        error_data = error.get("data")
                        
                        raise MCPError(error_message, error_code, error_data)
                    
                    # Log de sucesso
                    logger.debug(f"Requisição {method} bem-sucedida em {elapsed_ms:.1f}ms")
                    
                    return {
                        "result": result.get("result"),
                        "id": result.get("id"),
                        "latency_ms": elapsed_ms,
                        "timestamp": datetime.now().isoformat()
                    }
                    
            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Timeout na requisição {method} após {self.timeout}s")
                
            except (ConnectionError, MCPError, AuthenticationError):
                # Não fazer retry para estes erros
                raise
                
            except Exception as e:
                last_error = ConnectionError(f"Erro na requisição {method}: {str(e)}")
            
            # Delay antes da próxima tentativa
            if attempt < retries:
                delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                logger.debug(f"Aguardando {delay:.1f}s antes da próxima tentativa")
                await asyncio.sleep(delay)
        
        # Todas as tentativas falharam
        raise RetryError(f"Falha na requisição {method}", retries + 1, last_error)
    
    def _update_stats(self, latency_ms: float, success: bool):
        """Atualizar estatísticas de requisições"""
        self._stats["requests_sent"] += 1
        if success:
            self._stats["requests_successful"] += 1
        else:
            self._stats["requests_failed"] += 1
        
        self._stats["total_latency_ms"] += latency_ms
        self._stats["avg_latency_ms"] = (
            self._stats["total_latency_ms"] / self._stats["requests_sent"]
        )
        self._stats["last_request_time"] = datetime.now().isoformat()
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Listar todas as ferramentas disponíveis no servidor"""
        response = await self._make_request("tools/list")
        return response["result"].get("tools", [])
    
    async def list_resources(self) -> List[Dict[str, Any]]:
        """Listar todos os recursos disponíveis no servidor"""
        response = await self._make_request("resources/list")
        return response["result"].get("resources", [])
    
    async def call_tool(
        self, 
        tool_name: str, 
        arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Chamar uma ferramenta específica
        
        Args:
            tool_name: Nome da ferramenta
            arguments: Argumentos para a ferramenta
            
        Returns:
            Resultado da ferramenta
        """
        params = {"name": tool_name}
        if arguments:
            params["arguments"] = arguments
        
        response = await self._make_request("tools/call", params)
        return response["result"]
    
    async def get_resource(self, uri: str) -> str:
        """
        Obter um recurso específico
        
        Args:
            uri: URI do recurso
            
        Returns:
            Conteúdo do recurso
        """
        response = await self._make_request("resources/read", {"uri": uri})
        return response["result"]["contents"]
    
    def get_stats(self) -> Dict[str, Any]:
        """Obter estatísticas do cliente"""
        return {
            **self._stats,
            "connected": self._connected,
            "server_url": self.base_url,
            "session_id": self._session_id
        }
    
    @property
    def is_connected(self) -> bool:
        """Verificar se está conectado"""
        return self._connected and self._session is not None
    
    async def ping(self) -> float:
        """
        Fazer ping no servidor
        
        Returns:
            Latência em milissegundos
        """
        start_time = time.perf_counter()
        await self.list_tools()
        return (time.perf_counter() - start_time) * 1000
