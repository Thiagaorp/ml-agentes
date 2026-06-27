"""Agente Detector: encontra anúncios que prejudicam o algoritmo
(muita visita sem venda, saúde baixa, anúncio morto) e recomenda o que fazer."""
import cerebro
import config

SYSTEM = (
    "Você é um especialista no algoritmo de relevância do Mercado Livre. Anúncios com "
    "muitas visitas e zero vendas derrubam a taxa de conversão da conta e a relevância "
    "do vendedor. Para cada anúncio-problema, recomende UMA ação principal: "
    "pausar, reprecificar, reescrever (título/fotos/ficha) ou recriar do zero."
)


def detectar(anuncios):
    """Aplica regras para achar problemas e pede ao Claude a ação recomendada."""
    problemas = []
    for a in anuncios:
        if a["status"] != "active":
            continue
        visitas = a["visitas_30d"] or 0
        vendas = a["vendas_30d"] or 0
        saude = a["saude"]
        motivos = []
        if visitas >= config.MIN_VISITAS_SEM_VENDA and vendas == 0:
            motivos.append(f"{visitas} visitas em 30 dias e NENHUMA venda")
        if saude is not None and saude < config.SAUDE_MINIMA:
            motivos.append(f"saúde do anúncio baixa ({saude})")
        if visitas == 0:
            motivos.append("zero visitas em 30 dias (anúncio invisível)")
        if motivos:
            problemas.append({**a, "motivos": motivos})

    if not problemas:
        return {}

    # Processa em lotes para a resposta JSON do Claude nunca vir cortada.
    por_id = {}
    for i in range(0, len(problemas), 15):
        por_id.update(_consultar_lote(problemas[i:i + 15]))
    # anexa os motivos detectados pelas regras
    for p in problemas:
        if p["id"] in por_id:
            por_id[p["id"]]["motivos"] = p["motivos"]
    return por_id


def _consultar_lote(problemas):
    linhas = [
        f'- {p["id"]} | "{p["titulo"]}" | R$ {p["preco"]} | '
        f'visitas: {p["visitas_30d"] or 0} | vendas 30d: {p["vendas_30d"] or 0} | '
        f'vendas históricas: {p["vendas_totais"]} | problemas: {"; ".join(p["motivos"])}'
        for p in problemas
    ]

    prompt = f"""Estes anúncios estão prejudicando a relevância da conta no Mercado Livre:

{chr(10).join(linhas)}

Para CADA anúncio retorne:
- "id": id do anúncio
- "acao": "pausar" | "reprecificar" | "reescrever" | "recriar"
- "justificativa": 1 frase
- "detalhe": instrução específica (ex.: novo preço sugerido, o que mudar no título)

Retorne: {{"problemas": [ ... ]}}"""

    resultado = cerebro.perguntar_json(SYSTEM, prompt, max_tokens=4000,
                                       model=config.MODELO_DETECTOR)
    return {p["id"]: p for p in resultado.get("problemas", [])}
