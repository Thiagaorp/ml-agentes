"""Agentes de IA para vendedores do Mercado Livre.

Comandos:
  python main.py auth                  -> conectar sua conta do ML (uma vez)
  python main.py sync                  -> baixar anúncios, visitas e vendas
  python main.py analisar              -> rodar agentes analista + detector
  python main.py relatorio             -> gerar relatório HTML
  python main.py tudo                  -> sync + analisar + relatorio (rotina diária)
  python main.py palavras "produto"    -> pesquisa de palavras-chave
  python main.py criar produto.json    -> montar anúncio (dry-run; --publicar p/ subir)
  python main.py responder             -> responder perguntas (dry-run; --enviar p/ valer)
"""
import argparse
import json
import os
import sys

# Console/Log do Windows usa cp1252 e quebra nos emojis. Força UTF-8 na saída.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

import db
import notificar
import relatorio as rel
from agents import analista, atendente, criador, detector, palavras
from ml_api import MLClient


def cmd_auth(ml, _args):
    print("1) Abra esta URL no navegador e autorize o acesso:\n")
    print("   " + ml.auth_url())
    print("\n2) Depois do redirect, copie o valor de 'code' na URL.")
    code = input("\nCole o code aqui: ")
    ml.trocar_code(code)
    user = ml.me()
    print(f"\n✅ Conectado como {user['nickname']} (id {user['id']})")


def cmd_sync(ml, _args):
    print("🔄 Buscando anúncios...")
    ids = ml.meus_anuncios()
    print(f"   {len(ids)} anúncios encontrados")
    itens = ml.anuncios(ids)
    print("🔄 Buscando visitas (30d)...")
    visitas = ml.visitas_30d(ids)
    print("🔄 Buscando vendas (30d)...")
    vendas = ml.vendas_30d()
    print("🔄 Buscando saúde dos anúncios...")
    con = db.conectar()
    for item in itens:
        db.salvar_anuncio(con, item)
        saude = None
        if item["status"] == "active":
            h = ml.saude(item["id"])
            saude = h.get("health") if h else None
        db.salvar_metricas(con, item["id"], visitas.get(item["id"], 0),
                           vendas.get(item["id"], 0), saude)
    con.commit()
    print(f"✅ Sync completo: {len(itens)} anúncios salvos no banco local")


def cmd_analisar(ml, _args):
    con = db.conectar()
    painel = db.painel(con)
    if not painel:
        sys.exit("Banco vazio — rode antes: python main.py sync")

    print("🤖 Agente analista avaliando conversão de cada anúncio...")
    analises = analista.analisar(painel)
    for aid, a in analises.items():
        db.salvar_analise(con, aid, "analista", a)

    print("🤖 Agente detector procurando anúncios que prejudicam o algoritmo...")
    problemas = detector.detectar(painel)
    for aid, p in problemas.items():
        db.salvar_analise(con, aid, "detector", p)

    con.commit()
    urgentes = [a for a in analises.values() if a.get("nota") == "urgente"]
    print(f"✅ {len(analises)} anúncios analisados · "
          f"{len(urgentes)} urgentes · {len(problemas)} prejudicando o algoritmo")


def cmd_relatorio(ml, _args):
    con = db.conectar()
    painel = db.painel(con)
    analises = db.analises_de_hoje(con)
    # Na nuvem (GitHub Actions) não há navegador para abrir; lá o relatório vai pro Telegram.
    caminho = rel.gerar(painel, analises, abrir=not os.getenv("GITHUB_ACTIONS"))
    if notificar.enviar(painel, analises, caminho):
        print("📲 Resumo enviado para o Telegram")


def cmd_testar_telegram(ml, _args):
    notificar.testar()
    print("✅ Mensagem de teste enviada — confira o Telegram no celular.")


def cmd_tudo(ml, args):
    cmd_sync(ml, args)
    cmd_analisar(ml, args)
    cmd_relatorio(ml, args)


def cmd_palavras(ml, args):
    print(f'🔍 Pesquisando palavras-chave para "{args.termo}"...')
    r = palavras.pesquisar(ml, args.termo)
    print("\n🏆 Título sugerido:  " + r["titulo_sugerido"])
    for t in r.get("titulos_alternativos", []):
        print("   Alternativa:      " + t)
    print("\n🔑 Palavras principais: " + ", ".join(r["palavras_principais"]))
    print("📝 Secundárias (descrição/ficha): " + ", ".join(r.get("palavras_secundarias", [])))
    print("🚫 Evitar: " + ", ".join(r.get("evitar", [])))
    print("\n💡 " + r.get("observacao", ""))


def cmd_criar(ml, args):
    with open(args.arquivo, encoding="utf-8") as f:
        produto = json.load(f)
    criador.criar(ml, produto, publicar=args.publicar)


def cmd_responder(ml, args):
    atendente.responder(ml, enviar=args.enviar, limite=args.limite)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth")
    sub.add_parser("sync")
    sub.add_parser("analisar")
    sub.add_parser("relatorio")
    sub.add_parser("tudo")
    sub.add_parser("testar-telegram")
    pp = sub.add_parser("palavras")
    pp.add_argument("termo")
    pc = sub.add_parser("criar")
    pc.add_argument("arquivo", help="JSON com nome, preco, quantidade, fotos...")
    pc.add_argument("--publicar", action="store_true",
                    help="publica de verdade (sem isso é só simulação)")
    pr = sub.add_parser("responder")
    pr.add_argument("--enviar", action="store_true",
                    help="envia as respostas de verdade (sem isso é só simulação)")
    pr.add_argument("--limite", type=int, default=50,
                    help="máximo de perguntas por rodada (padrão 50)")
    args = p.parse_args()

    ml = MLClient()
    if args.cmd != "auth" and not ml.autenticado:
        sys.exit("Conta não conectada. Rode primeiro: python main.py auth")

    {"auth": cmd_auth, "sync": cmd_sync, "analisar": cmd_analisar,
     "relatorio": cmd_relatorio, "tudo": cmd_tudo, "palavras": cmd_palavras,
     "criar": cmd_criar, "responder": cmd_responder,
     "testar-telegram": cmd_testar_telegram}[args.cmd](ml, args)


if __name__ == "__main__":
    main()
