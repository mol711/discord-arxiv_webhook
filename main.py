import os
import yaml
import requests
import feedparser
from dotenv import load_dotenv

# 初期化
load_dotenv()

with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

#github actionsでのデバッグ用
print("DEEPL:", os.getenv("DEEPL_API_KEY"))
print("WEBHOOK:", os.getenv("DISCORD_WEBHOOK_URL"))

# arXiv取得
def fetch_arxiv():
    query = "+OR+".join([f"cat:{c}" for c in config["arxiv"]["categories"]])
    url = f"http://export.arxiv.org/api/query?search_query={query}&start=0&max_results={config['arxiv']['max_results']}"

    feed = feedparser.parse(url)

    papers = []
    for entry in feed.entries:
        papers.append({
            "title": entry.title,
            "summary": entry.summary.replace("\n", " "),
            "link": entry.link
        })

    return papers

# 要約(文字数制限)
def summarize(text):
    if not config["summary"]["enabled"]:
        return text

    return text[:config["summary"]["max_length"]] + "..."

# 翻訳(DeepL API)
def translate(text):
    if not config["translation"]["enabled"]:
        return text

    api_key = os.getenv("DEEPL_API_KEY")
    if not api_key:
        print("Error: DeepL APIKEY unset")
        return text

    url = "https://api-free.deepl.com/v2/translate" #有料版はエンドポイントが違うので注意

    headers = {
        "Authorization": f"DeepL-Auth-Key {api_key}"
    }

    data = {
        "text": text,
        "target_lang": config["translation"]["target_language"].upper()
    }

    response = requests.post(url, headers=headers, data=data)

    if response.status_code != 200:
        print("Error: Translation failed:", response.text)
        return text

    return response.json()["translations"][0]["text"]

# Discord投稿
def post_to_discord(paper):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        print("Error: Webhook URL unset")
        return

    embed = {
        "title": paper["title"],
        "description": paper["summary"],
        "url": paper["link"],
        "color": config["discord"]["color"]
    }

    data = {
        "username": config["discord"]["username"],
        "embeds": [embed]
    }

    requests.post(webhook_url, json=data)

# メイン処理
def main():
    papers = fetch_arxiv()

    selected = papers[:config["post"]["max_per_run"]]

    for paper in selected:
        # 要約
        paper["summary"] = summarize(paper["summary"])

        # 翻訳
        paper["title"] = translate(paper["title"])
        paper["summary"] = translate(paper["summary"])

        # 投稿
        post_to_discord(paper)

        print("Posted:", paper["title"])

# 実行
if __name__ == "__main__":
    main()