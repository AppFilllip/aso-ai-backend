from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
APPTWEAK_API_KEY = os.getenv("APPTWEAK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

app = FastAPI()

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Input schemas
class AppInfo(BaseModel):
    app_id: str
    app_store: str

class CountryInput(BaseModel):
    app_id: str
    country: str

class KeywordInput(BaseModel):
    app_id: str
    country: str
    competitors: list

class MetadataInput(BaseModel):
    keywords: list

@app.get("/")
def read_root():
    return {"message": "ASO AI Agent API is running. Visit /docs for Swagger UI."}

@app.post("/analyze")
def analyze_app(info: AppInfo):
    if info.app_store.lower() == "apple":
        if info.app_id.isdigit():
            url = f"https://itunes.apple.com/lookup?id={info.app_id}"
        else:
            url = f"https://itunes.apple.com/lookup?bundleId={info.app_id}"

        response = requests.get(url)
        data = response.json()
        if data.get("resultCount", 0) > 0:
            app_data = data["results"][0]
            return {
                "app_id": info.app_id,
                "store": "apple",
                "title": app_data.get("trackName"),
                "developer": app_data.get("sellerName"),
                "rating": app_data.get("averageUserRating"),
                "description": app_data.get("description"),
                "icon": app_data.get("artworkUrl100"),
                "status": "Success"
            }
        else:
            return {"status": "App not found on iTunes", "app_id": info.app_id}

    elif info.app_store.lower() == "google":
        try:
            url = f"https://play.google.com/store/apps/details?id={info.app_id}&hl=en&gl=us"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers)
            if response.status_code == 200 and "<title>" in response.text:
                start = response.text.find("<title>") + 7
                end = response.text.find("</title>", start)
                title = response.text[start:end].replace(" - Apps on Google Play", "")
                return {
                    "app_id": info.app_id,
                    "store": "google",
                    "title": title.strip(),
                    "status": "Success (og:title)"
                }
            else:
                return {"status": "App title not found in HTML", "app_id": info.app_id}
        except Exception as e:
            return {"status": f"Error fetching Play Store data: {str(e)}", "app_id": info.app_id}

    else:
        return {"status": "Unsupported store. Use 'apple' or 'google'"}

@app.post("/suggest-competitors")
def suggest_competitors(data: CountryInput):
    url = f"https://api.apptweak.com/api/v2/applications/{data.app_id}/competitors.json"
    params = {
        "country": data.country.lower(),
        "device": "iphone"
    }
    headers = {
        "Authorization": f"Bearer {APPTWEAK_API_KEY}"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        result = response.json()

        competitors = []
        for comp in result.get("competitors", []):
            competitors.append({
                "id": comp["application"]["id"],
                "name": comp["application"]["title"]
            })

        return { "competitors": competitors }

    except Exception as e:
        return {"error": str(e)}

@app.post("/fetch-keywords")
def fetch_keywords(data: KeywordInput):
    competitor_ids = ",".join(data.competitors)
    url = f"https://api.apptweak.com/api/v2/keywords/suggestions.json"
    params = {
        "country": data.country,
        "app_id": data.app_id,
        "competitors": competitor_ids,
        "auth_token": APPTWEAK_API_KEY
    }
    try:
        response = requests.get(url, params=params)
        keywords = response.json().get("content", {}).get("keywords", [])
        return {"suggested_keywords": keywords[:20]}
    except:
        return {"status": "Failed to fetch keywords"}

@app.post("/generate-metadata")
def generate_metadata(data: MetadataInput):
    prompt = f"Write ASO-optimized metadata for an app using these keywords: {', '.join(data.keywords)}.\nReturn title, subtitle, and description."
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert in App Store Optimization."},
                {"role": "user", "content": prompt}
            ]
        )
        response = completion.choices[0].message.content
        return {"generated_metadata": response.strip()}
    except Exception as e:
        return {"status": f"OpenAI error: {str(e)}"}
