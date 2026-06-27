"""Envia o resumo diário para o Telegram (notificação no celular do vendedor)."""
from datetime import date

import requests

import config

API = "https://api.telegram.org"


def _resumo(painel, analises):
    """Monta o texto do resumo: números do dia + lista de prioridades."""
    ativos = [a for a in painel if a["status"] == "active"]
    tot_v = sum(a["visitas_30d"] or 0 for a in ativos)
    tot_s = sum(a["vendas_30d"] or 0 for a in ativos)
    conv = round(tot_s / tot_v * 100, 2) if tot_v else 0

    urgentes = []
    for a in ativos:
        an = analises.get(a["id"], {})
        prob = an.get("detector")
        nota = (an.get("analista") or {}).get("nota")
        if prob or nota == "urgente":
            acao = (prob.get("acao") if prob else None) or nota or "revisar"
            urgentes.append(f"• {str(acao).upper()}: {a['titulo'][:55]}")

    linhas = [
        f"📊 Relatório Mercado Livre — {date.today().strftime('%d/%m/%Y')}",
        "",
        f"📦 {len(ativos)} anúncios ativos",
        f"👁 {tot_v} visitas (30d)",
        f"🛒 {tot_s} vendas (30d)",
        f"📈 {conv}% de conversão geral",
        f"🔴 {len(urgentes)} precisam de ação",
    ]
    if urgentes:
        linhas += ["", "Prioridades de hoje:"] + urgentes[:10]
        if len(urgentes) > 10:
            linhas.append(f"…e mais {len(urgentes) - 10}.")
    else:
        linhas += ["", "✅ Nenhum anúncio em estado crítico hoje."]
    return "\n".join(linhas)


def enviar(painel, analises, html_path=None):
    """Envia o resumo (e o HTML completo anexo) ao Telegram. Sem credenciais,
    não faz nada e retorna False."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return False

    base = f"{API}/bot{config.TELEGRAM_BOT_TOKEN}"
    r = requests.post(f"{base}/sendMessage", timeout=20, data={
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": _resumo(painel, analises),
        "disable_web_page_preview": True,
    })
    r.raise_for_status()

    if html_path:
        with open(html_path, "rb") as f:
            requests.post(f"{base}/sendDocument", timeout=60,
                          data={"chat_id": config.TELEGRAM_CHAT_ID,
                                "caption": "Relatório completo (abra no navegador)"},
                          files={"document": (html_path.name, f, "text/html")})
    return True


def testar():
    """Envia uma mensagem de teste — usado pelo comando `python main.py testar-telegram`."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        raise RuntimeError("Faltam TELEGRAM_BOT_TOKEN e/ou TELEGRAM_CHAT_ID.")
    r = requests.post(f"{API}/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage", timeout=20, data={
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": "✅ Conexão com o Telegram funcionando! "
                "Você vai receber o relatório do Mercado Livre por aqui.",
    })
    r.raise_for_status()
    return r.json()
