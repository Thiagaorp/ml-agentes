"""Agente Pós-venda: agradece a compra e pede avaliação para pedidos recentes.
Não manda duas vezes para o mesmo pedido (controle no banco local)."""
import cerebro
import config
import db

SYSTEM = (
    "Você escreve mensagens de pós-venda de uma loja do Mercado Livre Brasil. "
    "Tom cordial e breve, em português do Brasil. Agradeça a compra, coloque-se à "
    "disposição para dúvidas e peça gentilmente uma avaliação do produto. "
    "PROIBIDO pedir ou passar telefone, e-mail, WhatsApp, links ou qualquer contato "
    "fora do Mercado Livre (isso pune a conta). No máximo 3 frases. Trate por 'você'."
)


def processar(ml, enviar=False, dias=None):
    """Gera mensagens de pós-venda dos pedidos recentes. enviar=False (padrão) só
    mostra; enviar=True manda de verdade e marca o pedido como já avisado."""
    dias = dias or config.POSVENDA_DIAS
    seller_id = ml.me()["id"]
    pedidos = ml.pedidos_recentes(dias)
    con = db.conectar()

    elegiveis = [
        p for p in pedidos
        if p.get("status") not in ("cancelled", "invalid")
        and not db.posvenda_ja_enviado(con, p["id"])
    ]
    if not elegiveis:
        print("✅ Nenhum pedido novo para pós-venda.")
        return []

    print(f"📦 {len(elegiveis)} pedido(s) para pós-venda\n")
    resultados = []
    for p in elegiveis:
        buyer = p.get("buyer", {})
        nome = (buyer.get("first_name") or buyer.get("nickname") or "").strip()
        produtos = [oi["item"]["title"] for oi in p.get("order_items", [])]
        prompt = (f"Cliente: {nome or 'cliente'}\n"
                  f"Produto(s) comprado(s): {', '.join(produtos)}\n\n"
                  "Escreva a mensagem de pós-venda.")
        msg = cerebro.perguntar(SYSTEM, prompt, max_tokens=300,
                                model=config.MODELO_POSVENDA).strip()
        resultados.append({"pedido": p["id"], "cliente": nome, "mensagem": msg})

        print(f"🛒 Pedido {p['id']} — {nome or 'cliente'} ({', '.join(produtos)[:55]})")
        print(f"   💬 {msg}")
        if enviar:
            pack_id = p.get("pack_id") or p["id"]
            try:
                ml.enviar_mensagem_pos_venda(pack_id, seller_id, buyer["id"], msg)
                db.posvenda_marcar(con, p["id"])
                print("   ✅ Enviada")
            except Exception as e:
                print(f"   ⚠️ Falha ao enviar: {e}")
        print()

    if not enviar:
        print(f"[SIMULAÇÃO] {len(resultados)} mensagem(ns) prontas. Use --enviar para mandar.")
    return resultados
