# Agentes de IA para Mercado Livre

Sistema de 5 agentes de IA que otimizam o tempo de quem vende no Mercado Livre:

| Agente | O que faz |
|---|---|
| **Criador** | Sobe anúncios automaticamente a partir de uma descrição simples (categoria, título otimizado, atributos, descrição) |
| **Analista** | Avalia visitas, vendas e conversão de cada anúncio e diz o que mudar para converter mais |
| **Detector** | Encontra anúncios que prejudicam o algoritmo (visitas sem venda, saúde baixa) e recomenda pausar/reprecificar/reescrever |
| **Palavras-chave** | Cruza tendências do ML + autocomplete real + títulos dos concorrentes e monta o melhor título |
| **Atendente** | Responde as perguntas dos compradores usando só os dados reais do produto; quando não tem certeza, marca para você responder na mão |

## Instalação

```powershell
cd C:\Users\thiag\OneDrive\ml-agentes
pip install -r requirements.txt
copy .env.example .env
# edite o .env com suas credenciais do DevCenter ML e a chave da Anthropic
```

## Uso

```powershell
python main.py auth                # 1x: conecta sua conta do ML (OAuth)
python main.py tudo                # rotina diária: sync + análise + relatório HTML
python main.py palavras "fone bluetooth"   # pesquisa de palavras-chave
python main.py criar exemplo_produto.json  # monta anúncio (dry-run)
python main.py criar exemplo_produto.json --publicar  # publica de verdade
python main.py responder            # mostra as respostas que daria (simulação)
python main.py responder --enviar   # responde as perguntas de verdade
```

> **Atendente:** rode com frequência (o ML premia respostas rápidas) — ex. a cada
> 15 min via Task Scheduler: `python ...\main.py responder --enviar`. Em simulação
> (sem `--enviar`) ele nunca publica nada, só te mostra o que responderia.

O relatório diário fica em `relatorios\relatorio_AAAA-MM-DD.html` e abre sozinho no navegador.

Para rodar todo dia automaticamente, agende no Task Scheduler do Windows:
`python C:\Users\thiag\OneDrive\ml-agentes\main.py tudo`

## Roadmap para virar produto (fase 2)

O núcleo já é por conta (cada cliente conecta a própria conta ML via OAuth). Para vender:

1. **Backend mínimo (Cloudflare Worker)** — guarda o Client Secret e faz a troca do
   code OAuth por token, para o secret nunca ir no .exe distribuído. O redirect URI
   da aplicação ML aponta para o Worker.
2. **Licenciamento Kiwify** — webhook de compra gera chave de licença; o app valida
   a chave no Worker antes de rodar (mesmo modelo possível para o Financeiro ML).
3. **Custo de IA** — rotear as chamadas do Claude pelo Worker com a sua chave e
   limite mensal por licença (assinatura cobre o custo), em vez de expor a chave.
4. **Empacotar com PyInstaller** em .exe único, página de vendas no Cloudflare Pages.

## Arquitetura

```
main.py            CLI (auth, sync, analisar, relatorio, tudo, palavras, criar, responder)
ml_api.py          Cliente da API do ML (OAuth, itens, visitas, vendas, saúde, trends, perguntas)
db.py              SQLite local (anuncios, metricas, analises)
cerebro.py         Chamadas à API do Claude
agents/analista.py   agente de conversão
agents/detector.py   agente de anúncios-problema
agents/palavras.py   agente de palavras-chave
agents/criador.py    agente de criação de anúncios
agents/atendente.py  agente de respostas às perguntas dos compradores
relatorio.py       relatório diário em HTML
```
