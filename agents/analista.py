"""Agente Analista: avalia conversão de cada anúncio e recomenda otimizações."""
import cerebro
import config

SYSTEM = (
    "Você é um especialista em vendas e em Mercado Ads (a publicidade do Mercado "
    "Livre Brasil). Analisa métricas de anúncios e dá recomendações práticas e "
    "específicas para aumentar a conversão. Conversão boa no ML fica em geral acima "
    "de 1.5%; abaixo de 0.5% é ruim.\n"
    "Regra de ouro do Mercado Ads: só vale investir em anúncio quando a página JÁ "
    "converte. Critérios:\n"
    "- Boa conversão (>=1.5%) com poucas visitas, ou campeão de vendas → 'sim' "
    "(o anúncio está pronto, Ads escala o tráfego e tende a dar lucro).\n"
    "- Conversão baixa (<0.8%) ou saúde baixa → 'nao' (ajustar o anúncio antes; "
    "anunciar agora é pagar clique que não vira venda).\n"
    "- Casos intermediários ou anúncio novo sem histórico → 'testar' "
    "(começar com orçamento pequeno e ACOS-alvo conservador e observar).\n"
    "Quando recomendar 'sim' ou 'testar', sugira também:\n"
    "- orçamento diário INICIAL conservador, em reais, para coletar dados sem "
    "arriscar muito: geralmente R$ 10 a R$ 30/dia para produtos comuns, um pouco "
    "mais para ticket alto (preço acima de ~R$ 300). Em 'testar', use o piso da faixa.\n"
    "- ACOS-alvo (% da venda gasto em anúncio): deve ficar ABAIXO da margem de lucro "
    "do produto; na dúvida use 10-15%."
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
- "ads": objeto com a recomendação de Mercado Ads:
    - "vale": "sim" | "testar" | "nao"
    - "motivo": 1 frase curta justificando (ligada às métricas do anúncio)
    - "orcamento_dia": número em reais do orçamento diário inicial sugerido (0 se vale="nao")
    - "acos_alvo": número (% da venda) do ACOS-alvo sugerido (0 se vale="nao")

Retorne: {{"analises": [ ... ]}}"""

    resultado = cerebro.perguntar_json(SYSTEM, prompt, max_tokens=4000,
                                       model=config.MODELO_ANALISTA)
    return {a["id"]: a for a in resultado.get("analises", [])}
