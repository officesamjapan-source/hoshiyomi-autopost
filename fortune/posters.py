"""各 SNS への投稿処理。認証情報は引数で受け取る（複数アカウント対応）。

- Threads  : Threads API（graph.threads.net）
- Instagram: Instagram Graph API（graph.facebook.com、ビジネス/クリエイターアカウント）
- X        : X API v2（OAuth 1.0a ユーザーコンテキスト）

Threads と Instagram は「公開URLの画像」しか受け付けないため、
画像は GitHub リポジトリにコミットしてから raw URL を渡す。
"""
from __future__ import annotations

import time
from pathlib import Path

import requests

TIMEOUT = 60


def _check(resp: requests.Response, what: str) -> dict:
    if resp.status_code >= 400:
        raise RuntimeError(f"{what} 失敗 ({resp.status_code}): {resp.text[:500]}")
    return resp.json()


# ---------------- Threads ----------------
THREADS_API = "https://graph.threads.net/v1.0"


def _threads_wait(container_id: str, token: str) -> None:
    for _ in range(20):
        r = requests.get(f"{THREADS_API}/{container_id}",
                         params={"fields": "status,error_message", "access_token": token}, timeout=TIMEOUT)
        data = _check(r, "Threads ステータス確認")
        if data.get("status") == "FINISHED":
            return
        if data.get("status") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Threads メディア処理エラー: {data}")
        time.sleep(5)
    raise RuntimeError("Threads メディア処理がタイムアウトしました")


def _threads_publish(params: dict, token: str, user_id: str) -> str:
    # 本文は URL ではなくフォーム本文で送る（長い日本語で URL 長制限を超えないように）
    r = requests.post(f"{THREADS_API}/{user_id}/threads", data={**params, "access_token": token}, timeout=TIMEOUT)
    container_id = _check(r, "Threads コンテナ作成")["id"]
    _threads_wait(container_id, token)
    r = requests.post(f"{THREADS_API}/{user_id}/threads_publish",
                      data={"creation_id": container_id, "access_token": token}, timeout=TIMEOUT)
    return _check(r, "Threads 公開")["id"]


def post_threads(text: str, image_url: str | None, reply_text: str | None,
                 token: str, user_id: str = "me") -> str:
    params = {"media_type": "IMAGE", "image_url": image_url, "text": text} if image_url \
        else {"media_type": "TEXT", "text": text}
    post_id = _threads_publish(params, token, user_id)
    if reply_text:
        _threads_publish({"media_type": "TEXT", "text": reply_text, "reply_to_id": post_id}, token, user_id)
    return post_id


def recent_threads_texts(token: str, user_id: str = "me") -> list[str]:
    r = requests.get(f"{THREADS_API}/{user_id}/threads",
                     params={"fields": "text", "limit": 10, "access_token": token}, timeout=TIMEOUT)
    return [d.get("text") or "" for d in _check(r, "Threads 投稿一覧").get("data", [])]


# ---------------- Instagram ----------------
IG_API = "https://graph.facebook.com/v21.0"


def recent_instagram_captions(token: str, ig_user: str) -> list[str]:
    r = requests.get(f"{IG_API}/{ig_user}/media",
                     params={"fields": "caption", "limit": 10, "access_token": token}, timeout=TIMEOUT)
    return [d.get("caption") or "" for d in _check(r, "Instagram 投稿一覧").get("data", [])]


def post_instagram(caption: str, image_url: str, token: str, ig_user: str) -> str:
    r = requests.post(f"{IG_API}/{ig_user}/media",
                      data={"image_url": image_url, "caption": caption, "access_token": token}, timeout=TIMEOUT)
    container_id = _check(r, "Instagram コンテナ作成")["id"]
    for _ in range(20):
        r = requests.get(f"{IG_API}/{container_id}",
                         params={"fields": "status_code", "access_token": token}, timeout=TIMEOUT)
        status = _check(r, "Instagram ステータス確認").get("status_code")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram メディア処理エラー: {status}")
        time.sleep(5)
    else:
        raise RuntimeError("Instagram メディア処理がタイムアウトしました")
    r = requests.post(f"{IG_API}/{ig_user}/media_publish",
                      data={"creation_id": container_id, "access_token": token}, timeout=TIMEOUT)
    return _check(r, "Instagram 公開")["id"]


# ---------------- X ----------------
X_API = "https://api.x.com/2"


def post_x(text: str, image_path: Path | None, reply_text: str | None,
           api_key: str, api_secret: str, access_token: str, access_secret: str) -> str:
    from requests_oauthlib import OAuth1Session

    s = OAuth1Session(api_key, client_secret=api_secret,
                      resource_owner_key=access_token, resource_owner_secret=access_secret)
    body: dict = {"text": text}
    if image_path:
        try:
            with open(image_path, "rb") as f:
                r = s.post(f"{X_API}/media/upload",
                           files={"media": (image_path.name, f, "image/jpeg")},
                           data={"media_category": "tweet_image"}, timeout=TIMEOUT)
            media_id = _check(r, "X 画像アップロード")["data"]["id"]
            body["media"] = {"media_ids": [media_id]}
        except Exception as e:  # 画像だけ失敗しても文章は投稿する
            print(f"[warn] X の画像アップロードに失敗、文章のみ投稿します: {e}")
    r = s.post(f"{X_API}/tweets", json=body, timeout=TIMEOUT)
    tweet_id = _check(r, "X 投稿")["data"]["id"]
    if reply_text:
        r = s.post(f"{X_API}/tweets",
                   json={"text": reply_text, "reply": {"in_reply_to_tweet_id": tweet_id}}, timeout=TIMEOUT)
        _check(r, "X リプライ")
    return tweet_id
