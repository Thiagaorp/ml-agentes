"""Gera o relatório diário em HTML com métricas e recomendações dos agentes."""
import webbrowser
from datetime import date

import config

CORES_NOTA = {"otimo": "#16a34a", "ok": "#2563eb", "otimizar": "#d97706", "urgente": "#dc2626"}


def gerar(painel, analises, abrir=True):
    config.RELATORIOS_DIR.mkdir(exist_ok=True)
    hoje = date.today().isoformat()

    ativos = [a for a in painel if a["status"] == "active"]
    tot_visitas = sum(a["visitas_30d"] or 0 for a in ativos)
    tot_vendas = sum(a["vendas_30d"] or 0 for a in ativos)
    conv_geral = round(tot_vendas / tot_visitas * 100, 2) if tot_visitas else 0
    urgentes = sum(
        1 for an in analises.values()
        if an.get("detector") or (an.get("analista") or {}).get("nota") == "urgente"
    )

    linhas = ""
    for a in ativos:
        an = analises.get(a["id"], {})
        analise = an.get("analista") or {}
        problema = an.get("detector")
        nota = analise.get("nota", "-")
        cor = CORES_NOTA.get(nota, "#6b7280")
        acoes = "".join(f"<li>{ac}</li>" for ac in analise.get("acoes", []))
        ads = analise.get("ads") or {}
        ads_html = ""
        if ads.get("vale"):
            rotulo = {"sim": "VALE A PENA", "testar": "TESTAR", "nao": "AGORA NÃO"}
            sugestao = ""
            if ads["vale"] != "nao" and ads.get("orcamento_dia"):
                sugestao = (f'<br>💰 Sugestão: R$ {ads["orcamento_dia"]}/dia'
                            f' · 🎯 ACOS-alvo {ads.get("acos_alvo", "-")}%')
            ads_html = (f'<div class="ads ads-{ads["vale"]}">📣 Mercado Ads: '
                        f'<b>{rotulo.get(ads["vale"], ads["vale"].upper())}</b> — '
                        f'{ads.get("motivo", "")}{sugestao}</div>')
        alerta = ""
        if problema:
            alerta = (f'<div class="alerta">⚠️ <b>{problema.get("acao", "").upper()}</b> — '
                      f'{problema.get("justificativa", "")}<br>{problema.get("detalhe", "")}</div>')
        linhas += f"""
        <tr>
          <td><a href="{a['permalink']}" target="_blank">{a['titulo']}</a><br>
              <small>{a['id']} · R$ {a['preco']}</small>{alerta}</td>
          <td>{a['visitas_30d'] or 0}</td>
          <td>{a['vendas_30d'] or 0}</td>
          <td>{a['conversao'] or 0}%</td>
          <td>{a['saude'] if a['saude'] is not None else '-'}</td>
          <td><span class="nota" style="background:{cor}">{nota}</span><br>
              <small>{analise.get('diagnostico', '')}</small>
              <ul>{acoes}</ul>{ads_html}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>Relatório ML — {hoje}</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; margin: 24px; background: #f8fafc; color: #1e293b; }}
  h1 {{ font-size: 22px; }}
  .cards {{ display: flex; gap: 16px; margin: 16px 0; flex-wrap: wrap; }}
  .card {{ background: #fff; border-radius: 10px; padding: 16px 24px; box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
  .card b {{ font-size: 26px; display: block; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
  th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #e2e8f0; vertical-align: top; font-size: 14px; }}
  th {{ background: #1e293b; color: #fff; }}
  .nota {{ color: #fff; padding: 2px 10px; border-radius: 99px; font-size: 12px; font-weight: 600; }}
  .alerta {{ background: #fef2f2; border-left: 3px solid #dc2626; padding: 6px 10px; margin-top: 6px; font-size: 13px; border-radius: 4px; }}
  .ads {{ padding: 6px 10px; margin-top: 6px; font-size: 13px; border-radius: 4px; border-left: 3px solid #6b7280; background: #f1f5f9; }}
  .ads-sim {{ border-color: #16a34a; background: #f0fdf4; }}
  .ads-testar {{ border-color: #d97706; background: #fffbeb; }}
  .ads-nao {{ border-color: #6b7280; background: #f8fafc; }}
  ul {{ margin: 6px 0 0 16px; padding: 0; }}
  small {{ color: #64748b; }}
</style></head><body>
<h1>📊 Relatório Mercado Livre — {hoje}</h1>
<div class="cards">
  <div class="card"><b>{len(ativos)}</b>anúncios ativos</div>
  <div class="card"><b>{tot_visitas}</b>visitas (30d)</div>
  <div class="card"><b>{tot_vendas}</b>vendas (30d)</div>
  <div class="card"><b>{conv_geral}%</b>conversão geral</div>
  <div class="card" style="color:#dc2626"><b>{urgentes}</b>precisam de ação</div>
</div>
<table>
<tr><th>Anúncio</th><th>Visitas 30d</th><th>Vendas 30d</th><th>Conversão</th><th>Saúde</th><th>Análise do agente</th></tr>
{linhas}
</table>
</body></html>"""

    caminho = config.RELATORIOS_DIR / f"relatorio_{hoje}.html"
    caminho.write_text(html, encoding="utf-8")
    print(f"📄 Relatório salvo em: {caminho}")
    if abrir:
        webbrowser.open(caminho.as_uri())
    return caminho
