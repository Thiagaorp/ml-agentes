"""Agente de Preço: compara com os concorrentes do mesmo produto e sugere um
preço competitivo, respeitando uma trava de preço mínimo (PRECO_PISO_PCT) para
nunca vender no prejuízo. A trava é aplicada no código, não confia na IA."""
import cerebro
import config

SYSTEM = (
    "Você é especialista em precificação no Mercado Livre Brasil. Recomenda preço "
    "competitivo com base nos concorrentes do MESMO produto, mas sabe que ser o mais "
    "barato nem sempre é o melhor (reputação, frete grátis e Full também vendem). "
    "Nunca sugira preço de prejuízo nem abaixo do mínimo informado."
)


def sugerir(ml, painel, aplicar=False, limite=None):
    """Sugere (ou aplica, com aplicar=True) novo preço por anúncio ativo."""
    ativos = [a for a in painel if a["status"] == "active"]
    if limite:
        ativos = ativos[:limite]
    if not ativos:
        print("Nenhum anúncio ativo.")
        return []

    print(f"💲 Avaliando preço de {len(ativos)} anúncio(s)\n")
    resultados = []
    for a in ativos:
        try:
            busca = ml.buscar(a["titulo"], limit=15)
            conc = [{"preco": r["price"], "vendidos": r.get("sold_quantity", 0)}
                    for r in busca.get("results", []) if r["id"] != a["id"]]
        except Exception:
            conc = []

        piso = round(a["preco"] * config.PRECO_PISO_PCT, 2)
        prompt = (
            f'Seu anúncio: "{a["titulo"]}" — preço atual R$ {a["preco"]}\n'
            f"Suas vendas (30d): {a.get('vendas_30d') or 0}\n"
            "Concorrentes (preço | vendidos): "
            + ("; ".join(f"R$ {c['preco']}/{c['vendidos']}" for c in conc[:12]) or "(sem dados)")
            + f"\n\nPreço MÍNIMO permitido: R$ {piso} (nunca abaixo disso).\n"
            'Retorne JSON: {"acao": "manter"|"baixar"|"subir", '
            '"preco_sugerido": número, "motivo": "1 frase curta"}'
        )
        r = cerebro.perguntar_json(SYSTEM, prompt, max_tokens=300,
                                   model=config.MODELO_PRECO)

        sugerido = float(r.get("preco_sugerido") or a["preco"])
        sugerido = max(sugerido, piso)            # trava de segurança no código
        r.update(id=a["id"], preco_atual=a["preco"], preco_final=round(sugerido, 2))
        resultados.append(r)

        muda = abs(r["preco_final"] - a["preco"]) >= 0.01
        print(f'💲 {a["titulo"][:55]}')
        print(f'   R$ {a["preco"]} → R$ {r["preco_final"]}  ({r.get("acao", "")}) — {r.get("motivo", "")}')
        if aplicar and muda:
            try:
                ml.atualizar_anuncio(a["id"], {"price": r["preco_final"]})
                print("   ✅ Preço atualizado")
            except Exception as e:
                print(f"   ⚠️ Falha ao atualizar: {e}")
        print()

    if not aplicar:
        n = sum(1 for r in resultados if abs(r["preco_final"] - r["preco_atual"]) >= 0.01)
        print(f"[SIMULAÇÃO] {n} anúncio(s) teriam mudança de preço. Use --aplicar para valer.")
    return resultados
