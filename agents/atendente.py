"""Agente Atendente: responde automaticamente as perguntas dos compradores nos
anúncios, usando SOMENTE os dados reais do produto. Quando não tem certeza da
resposta, ele NÃO responde — marca a pergunta para você responder na mão."""
import json

import cerebro
import config

SYSTEM = (
    "Você é o atendente de uma loja no Mercado Livre Brasil. Responde perguntas de "
    "compradores de forma curta, educada e objetiva, em português do Brasil.\n"
    "REGRAS OBRIGATÓRIAS:\n"
    "- Use SOMENTE as informações do produto fornecidas. Nunca invente medida, "
    "compatibilidade, prazo de entrega ou estoque que não esteja nos dados.\n"
    "- Proibido pedir ou passar telefone, e-mail, WhatsApp, links ou combinar venda "
    "fora do Mercado Livre — isso pune a conta.\n"
    "- Se a pergunta não puder ser respondida com segurança pelos dados, marque para "
    "atendimento humano em vez de chutar.\n"
    "- No máximo 2 frases. Trate o cliente por 'você'."
)


def _contexto_produto(ml, item_id, cache):
    """Monta (e guarda em cache) o contexto do anúncio para a IA responder."""
    if item_id in cache:
        return cache[item_id]
    item = ml.anuncio(item_id)
    attrs = {a["name"]: a.get("value_name") for a in item.get("attributes", [])
             if a.get("value_name")}
    ctx = {
        "titulo": item.get("title"),
        "preco": item.get("price"),
        "disponivel": item.get("available_quantity"),
        "condicao": item.get("condition"),
        "frete_gratis": item.get("shipping", {}).get("free_shipping", False),
        "atributos": attrs,
        "descricao": ml.descricao(item_id)[:1500],
    }
    cache[item_id] = ctx
    return ctx


def responder(ml, enviar=False, limite=50):
    """Lê as perguntas pendentes e gera respostas. Com enviar=False (padrão) só
    mostra o que responderia; enviar=True publica de fato a resposta ao comprador."""
    perguntas = ml.perguntas_pendentes(limite)
    if not perguntas:
        print("✅ Nenhuma pergunta pendente.")
        return []

    print(f"💬 {len(perguntas)} pergunta(s) pendente(s)\n")
    cache, resultados = {}, []
    for q in perguntas:
        ctx = _contexto_produto(ml, q["item_id"], cache)
        prompt = f"""Produto:
{json.dumps(ctx, ensure_ascii=False, indent=2)}

Pergunta do comprador: "{q['text']}"

Retorne JSON:
- "responder": true só se dá para responder com segurança pelos dados acima
- "resposta": a resposta pronta para enviar (máx. 2 frases) — vazio se responder=false
- "motivo": se responder=false, por que precisa de atendimento humano"""

        r = cerebro.perguntar_json(SYSTEM, prompt, max_tokens=400,
                                   model=config.MODELO_ATENDENTE)
        r.update(question_id=q["id"], pergunta=q["text"], item_id=q["item_id"])
        resultados.append(r)

        print(f'❓ {q["text"]}')
        print(f'   📦 {ctx["titulo"]}')
        if r.get("responder") and r.get("resposta"):
            print(f'   💡 {r["resposta"]}')
            if enviar:
                ml.responder_pergunta(q["id"], r["resposta"])
                print("   ✅ Enviada")
        else:
            print(f'   ⚠️  Atendimento humano: {r.get("motivo", "sem confiança na resposta")}')
        print()

    if not enviar:
        respondiveis = sum(1 for r in resultados if r.get("responder"))
        print(f"[SIMULAÇÃO] {respondiveis}/{len(resultados)} seriam respondidas "
              "automaticamente. Use --enviar para responder de verdade.")
    return resultados
