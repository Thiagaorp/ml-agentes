"""Agente de Palavras-chave: cruza tendências do ML, autocomplete e títulos dos
concorrentes mais vendidos para montar o melhor título e termos de cada produto."""
import cerebro
import config

SYSTEM = (
    "Você é um especialista em SEO do Mercado Livre Brasil. Títulos têm no máximo 60 "
    "caracteres e o formato vencedor é: Produto + Marca + Modelo + Especificação. "
    "Sem pontuação desnecessária, sem palavras vazias como 'promoção' ou 'imperdível'."
)


def pesquisar(ml, termo, categoria=None):
    """Retorna palavras-chave recomendadas e título sugerido para o termo/produto."""
    sugestoes = ml.autosugestao(termo)

    tend = ml.tendencias(categoria)
    tendencias = [t["keyword"] for t in tend[:25]] if tend else []

    try:
        busca = ml.buscar(termo, limit=20)
        concorrentes = [
            {"titulo": r["title"], "preco": r["price"], "vendidos": r.get("sold_quantity", 0)}
            for r in busca.get("results", [])
        ]
    except Exception:
        concorrentes = []

    prompt = f"""Produto/termo pesquisado: "{termo}"

O que os compradores digitam no ML (autocomplete real):
{chr(10).join("- " + s for s in sugestoes) or "- (sem dados)"}

Buscas em alta na categoria:
{chr(10).join("- " + t for t in tendencias) or "- (sem dados)"}

Títulos dos 20 primeiros resultados (concorrentes):
{chr(10).join(f'- "{c["titulo"]}" | R$ {c["preco"]} | {c["vendidos"]} vendidos' for c in concorrentes) or "- (sem dados)"}

Retorne JSON:
- "palavras_principais": 5 a 8 palavras/termos que DEVEM estar no anúncio (ordem de importância)
- "palavras_secundarias": termos para usar na descrição e ficha técnica
- "evitar": termos que atrapalham
- "titulo_sugerido": o melhor título possível (máx. 60 caracteres)
- "titulos_alternativos": 2 variações
- "observacao": 1 insight sobre o que os concorrentes que mais vendem fazem"""

    return cerebro.perguntar_json(SYSTEM, prompt, max_tokens=2000,
                                  model=config.MODELO_PALAVRAS)
