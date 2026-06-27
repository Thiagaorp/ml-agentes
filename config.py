import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

ML_CLIENT_ID = os.getenv("ML_CLIENT_ID", "")
ML_CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET", "")
ML_REDIRECT_URI = os.getenv("ML_REDIRECT_URI", "")
ML_SITE = os.getenv("ML_SITE", "MLB")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
# Modelo padrao (fallback). Cada agente pode ter o seu proprio abaixo.
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# Modelo por agente:
#  - analista/detector rodam em loop diario em muitos anuncios -> Haiku (barato/rapido)
#  - criador/palavras geram texto que o cliente le -> Sonnet (mais qualidade)
HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-6"
MODELO_ANALISTA = os.getenv("MODELO_ANALISTA", HAIKU)
MODELO_DETECTOR = os.getenv("MODELO_DETECTOR", HAIKU)
MODELO_PALAVRAS = os.getenv("MODELO_PALAVRAS", SONNET)
MODELO_CRIADOR = os.getenv("MODELO_CRIADOR", SONNET)
# atendente responde o cliente direto -> Sonnet (qualidade > custo)
MODELO_ATENDENTE = os.getenv("MODELO_ATENDENTE", SONNET)

DB_PATH = BASE_DIR / "dados.db"
TOKEN_PATH = BASE_DIR / "token.json"
RELATORIOS_DIR = BASE_DIR / "relatorios"

# Regras do detector de anuncios-problema
MIN_VISITAS_SEM_VENDA = 50   # visitas em 30 dias sem nenhuma venda = problema
SAUDE_MINIMA = 0.75          # health do ML abaixo disso = problema
