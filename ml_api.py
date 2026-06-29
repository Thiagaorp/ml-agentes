"""Cliente da API do Mercado Livre: OAuth 2.0 + endpoints usados pelos agentes."""
import json
import time
from datetime import datetime, timedelta

import requests

import config

API = "https://api.mercadolibre.com"
AUTH_HOST = {
    "MLB": "https://auth.mercadolivre.com.br",
    "MLA": "https://auth.mercadolibre.com.ar",
    "MLM": "https://auth.mercadolibre.com.mx",
}


class MLClient:
    def __init__(self):
        self.client_id = config.ML_CLIENT_ID
        self.client_secret = config.ML_CLIENT_SECRET
        self.redirect_uri = config.ML_REDIRECT_URI
        self.site = config.ML_SITE
        self._token = self._carregar_token()

    # ---------- OAuth ----------

    def auth_url(self):
        host = AUTH_HOST.get(self.site, AUTH_HOST["MLB"])
        return (
            f"{host}/authorization?response_type=code"
            f"&client_id={self.client_id}&redirect_uri={self.redirect_uri}"
        )

    def trocar_code(self, code):
        """Troca o code do redirect por access_token + refresh_token."""
        resp = requests.post(f"{API}/oauth/token", data={
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code.strip(),
            "redirect_uri": self.redirect_uri,
        })
        resp.raise_for_status()
        self._salvar_token(resp.json())
        return self._token

    def _refresh(self):
        resp = requests.post(f"{API}/oauth/token", data={
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self._token["refresh_token"],
        })
        resp.raise_for_status()
        self._salvar_token(resp.json())

    def _salvar_token(self, dados):
        dados["expira_em"] = time.time() + dados.get("expires_in", 21600) - 300
        config.TOKEN_PATH.write_text(json.dumps(dados, indent=2))
        self._token = dados

    def _carregar_token(self):
        if config.TOKEN_PATH.exists():
            return json.loads(config.TOKEN_PATH.read_text())
        return None

    @property
    def autenticado(self):
        return self._token is not None

    def _headers(self):
        if not self._token:
            raise RuntimeError("Não autenticado. Rode: python main.py auth")
        if time.time() >= self._token.get("expira_em", 0):
            self._refresh()
        return {"Authorization": f"Bearer {self._token['access_token']}"}

    def _get(self, path, **params):
        resp = requests.get(f"{API}{path}", headers=self._headers(), params=params)
        if resp.status_code == 401:
            self._refresh()
            resp = requests.get(f"{API}{path}", headers=self._headers(), params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path, payload):
        resp = requests.post(f"{API}{path}", headers=self._headers(), json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(f"Erro {resp.status_code} em POST {path}: {resp.text}")
        return resp.json()

    def _put(self, path, payload):
        resp = requests.put(f"{API}{path}", headers=self._headers(), json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(f"Erro {resp.status_code} em PUT {path}: {resp.text}")
        return resp.json()

    # ---------- Conta e anúncios ----------

    def me(self):
        return self._get("/users/me")

    def meus_anuncios(self, status=None):
        """Retorna todos os IDs de anúncios do vendedor (via scan/scroll)."""
        uid = self.me()["id"]
        ids, scroll = [], None
        while True:
            params = {"search_type": "scan", "limit": 100}
            if status:
                params["status"] = status
            if scroll:
                params["scroll_id"] = scroll
            data = self._get(f"/users/{uid}/items/search", **params)
            ids += data.get("results", [])
            scroll = data.get("scroll_id")
            if not scroll or not data.get("results"):
                break
        return ids

    def anuncio(self, item_id):
        return self._get(f"/items/{item_id}", include_attributes="all")

    def anuncios(self, item_ids):
        """Multiget de anúncios, em lotes de 20."""
        out = []
        for i in range(0, len(item_ids), 20):
            lote = ",".join(item_ids[i:i + 20])
            data = self._get("/items", ids=lote)
            out += [d["body"] for d in data if d.get("code") == 200]
        return out

    def visitas_30d(self, item_ids):
        """Visitas dos últimos 30 dias por anúncio. Retorna {item_id: visitas}.
        O ML passou a aceitar só 1 item por consulta de visitas, então é um
        request por anúncio (endpoint time_window)."""
        out = {}
        for iid in item_ids:
            try:
                data = self._get(f"/items/{iid}/visits/time_window", last=30, unit="day")
                out[iid] = data.get("total_visits", 0)
            except requests.HTTPError:
                out[iid] = 0
        return out

    def vendas_30d(self):
        """Vendas dos últimos 30 dias por anúncio. Retorna {item_id: qtd_vendida}."""
        uid = self.me()["id"]
        ini = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00.000-03:00")
        vendas, offset = {}, 0
        while True:
            data = self._get(
                "/orders/search", seller=uid, limit=50, offset=offset,
                sort="date_desc", **{"order.date_created.from": ini},
            )
            for pedido in data.get("results", []):
                if pedido.get("status") == "cancelled":
                    continue
                for oi in pedido.get("order_items", []):
                    iid = oi["item"]["id"]
                    vendas[iid] = vendas.get(iid, 0) + oi.get("quantity", 1)
            offset += 50
            if offset >= min(data.get("paging", {}).get("total", 0), 1000):
                break
        return vendas

    def saude(self, item_id):
        """Health do anúncio (0 a 1) + ações sugeridas pelo próprio ML."""
        try:
            return self._get(f"/items/{item_id}/health")
        except requests.HTTPError:
            return None

    # ---------- Pesquisa de mercado ----------

    def tendencias(self, category_id=None):
        path = f"/trends/{self.site}/{category_id}" if category_id else f"/trends/{self.site}"
        try:
            return self._get(path)
        except requests.HTTPError:
            return []

    def buscar(self, termo, limit=20):
        return self._get(f"/sites/{self.site}/search", q=termo, limit=limit)

    def autosugestao(self, termo):
        """Autocomplete do ML — o que os compradores realmente digitam."""
        try:
            resp = requests.get(
                "https://http2.mlstatic.com/resources/sites/" + self.site + "/autosuggest",
                params={"q": termo, "showFilters": "true", "limit": 10, "api_version": "2"},
                timeout=10,
            )
            data = resp.json()
            return [s["q"] for s in data.get("suggested_queries", [])]
        except Exception:
            return []

    def descobrir_categoria(self, nome_produto):
        """Prediz a categoria certa para um produto."""
        data = self._get(
            f"/sites/{self.site}/domain_discovery/search", q=nome_produto, limit=1
        )
        return data[0] if data else None

    # ---------- Pedidos e pós-venda ----------

    def pedidos_recentes(self, dias=7):
        """Pedidos dos últimos N dias (com comprador, itens, status, pack)."""
        uid = self.me()["id"]
        ini = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%dT00:00:00.000-03:00")
        pedidos, offset = [], 0
        while True:
            data = self._get(
                "/orders/search", seller=uid, limit=50, offset=offset,
                sort="date_desc", **{"order.date_created.from": ini},
            )
            pedidos += data.get("results", [])
            offset += 50
            if offset >= min(data.get("paging", {}).get("total", 0), 500):
                break
        return pedidos

    def enviar_mensagem_pos_venda(self, pack_id, seller_id, buyer_id, texto):
        """Manda mensagem pós-venda ao comprador (sobre um pedido/pack)."""
        return self._post(
            f"/messages/packs/{pack_id}/sellers/{seller_id}?tag=post_sale",
            {"from": {"user_id": str(seller_id)},
             "to": {"user_id": str(buyer_id)},
             "text": texto},
        )

    # ---------- Perguntas e respostas ----------

    def perguntas_pendentes(self, limit=50):
        """Perguntas ainda não respondidas dos compradores (mais antigas primeiro)."""
        uid = self.me()["id"]
        data = self._get(
            "/questions/search", seller_id=uid, status="UNANSWERED",
            sort_fields="date_created", sort_types="ASC", limit=limit, api_version=4,
        )
        return data.get("questions", [])

    def responder_pergunta(self, question_id, texto):
        """Publica a resposta de uma pergunta. Cuidado: é visível ao comprador."""
        return self._post("/answers", {"question_id": question_id, "text": texto})

    def descricao(self, item_id):
        """Texto puro da descrição do anúncio (string vazia se não tiver)."""
        try:
            return self._get(f"/items/{item_id}/description").get("plain_text", "")
        except requests.HTTPError:
            return ""

    # ---------- Ações ----------

    def upload_foto(self, caminho):
        """Sobe uma imagem do disco para o CDN do Mercado Livre e retorna o
        picture_id, que pode ir no payload do anúncio como {"id": picture_id}."""
        with open(caminho, "rb") as f:
            resp = requests.post(f"{API}/pictures/items/upload",
                                 headers=self._headers(), files={"file": f})
        if resp.status_code >= 400:
            raise RuntimeError(f"Erro {resp.status_code} ao subir foto {caminho}: {resp.text}")
        return resp.json()["id"]

    def criar_anuncio(self, payload):
        return self._post("/items", payload)

    def atualizar_anuncio(self, item_id, payload):
        return self._put(f"/items/{item_id}", payload)

    def pausar_anuncio(self, item_id):
        return self._put(f"/items/{item_id}", {"status": "paused"})
