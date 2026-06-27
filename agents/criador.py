"""Agente Criador: monta e publica anúncios automaticamente a partir de uma
descrição simples do produto. Usa o agente de palavras-chave para o título."""
import json

import cerebro
import config
from agents import palavras

SYSTEM = (
    "Você monta anúncios para a API do Mercado Livre (POST /items). Gere payloads "
    "completos e válidos. Preço em número, currency_id BRL, condition new salvo "
    "indicação contrária. Preencha o máximo de atributos da categoria."
)


def criar(ml, produto, publicar=False):
    """produto = dict com: nome, preco, quantidade, descricao (opcional),
    fotos (lista de URLs, opcional), condicao (opcional).
    Com publicar=False só mostra o payload (dry-run)."""
    cat = ml.descobrir_categoria(produto["nome"])
    if not cat:
        raise RuntimeError(f"Não achei categoria para: {produto['nome']}")

    kw = palavras.pesquisar(ml, produto["nome"], cat.get("category_id"))

    prompt = f"""Monte o payload JSON para criar este anúncio no Mercado Livre:

Produto: {json.dumps(produto, ensure_ascii=False)}
Categoria prevista pelo ML: {json.dumps(cat, ensure_ascii=False)}
Título sugerido pelo agente de palavras-chave: "{kw["titulo_sugerido"]}"
Palavras que devem aparecer: {", ".join(kw["palavras_principais"])}

Retorne JSON com exatamente estas chaves:
- "title" (use o título sugerido, máx. 60 caracteres)
- "category_id"
- "price", "currency_id", "available_quantity", "condition"
- "listing_type_id": "gold_special"
- "pictures": lista de {{"source": url}} (use as fotos fornecidas)
- "attributes": lista de {{"id", "value_name"}} com os atributos que você conseguir inferir
- "description_text": descrição vendedora em texto puro (será enviada separadamente)"""

    payload = cerebro.perguntar_json(SYSTEM, prompt, max_tokens=3000,
                                     model=config.MODELO_CRIADOR)
    descricao = payload.pop("description_text", produto.get("descricao", ""))

    print("\n=== PAYLOAD DO ANÚNCIO ===")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print("\n=== DESCRIÇÃO ===\n" + descricao)
    print("\n=== PALAVRAS-CHAVE USADAS ===")
    print(", ".join(kw["palavras_principais"]))

    if not publicar:
        print("\n[DRY-RUN] Nada foi publicado. Use --publicar para subir o anúncio.")
        return None

    item = ml.criar_anuncio(payload)
    if descricao:
        ml._post(f"/items/{item['id']}/description", {"plain_text": descricao})
    print(f"\n✅ Anúncio publicado: {item['id']} — {item.get('permalink')}")
    return item
