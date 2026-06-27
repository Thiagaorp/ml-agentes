"""Agente Analista: avalia conversão de cada anúncio e recomenda otimizações."""
import cerebro
import config

SYSTEM = (
    "Você é um especialista em vendas no Mercado Livre Brasil. Analisa métricas de "
    "anúncios e dá recomendações práticas e específicas para aumentar a conversão. "
    "Conversão boa no ML fica em geral acima de 1.5%; abaixo de 0.5% é ruim."
)


def analisar(anuncios):
    """Recebe a lista do painel (id, titulo, preco, visitas_30d, vendas_30d,
    conversao, saude...) e devolve {anuncio_id: analise}.
    Processa em lotes para a resposta JSON do Claude nunca estourar o limite de tokens."""
    ativos = [a for a in anuncios if a["status"] == "active"]
    out = {}
    for i in range(0, len(ativos), 15):
        out.update(_analisar_lote(ativos[i:i + 15]))
    return out


def _analisar_lote(ativos):
    linhas = []
    for a in ativos:
        linhas.append(
            f'- {a["id"]} | "{a["titulo"]}" | R$ {a["preco"]} | '
            f'visitas 30d: {a["visitas_30d"] or 0} | vendas 30d: {a["vendas_30d"] or 0} | '
            f'conversão: {a["conversao"] or 0}% | saúde ML: {a["saude"]} | '
            f'frete grátis: {"sim" if a["frete_gratis"] else "não"}'
        )

    prompt = f"""Analise estes anúncios ativos de um vendedor do Mercado Livre (métricas dos últimos 30 dias):

{chr(10).join(linhas)}

Para CADA anúncio, retorne um objeto JSON com:
- "id": id do anúncio
- "nota": "otimo" | "ok" | "otimizar" | "urgente"
- "diagnostico": 1 frase explicando o desempenho
- "acoes": lista de 1 a 3 ações concretas e específicas (ex.: "trocar primeira foto por fundo branco", "reduzir preço para R$ X para bater o concorrente", "reescrever título incluindo a palavra Y")

Retorne: {{"analises": [ ... ]}}"""

    resultado = cerebro.perguntar_json(SYSTEM, prompt, max_tokens=4000,
                                       model=config.MODELO_ANALISTA)
    return {a["id"]: a for a in resultado.get("analises", [])}
