@app.post("/suggest-competitors")
def suggest_competitors(data: CountryInput):
    apptweak_key = os.getenv("APPTWEAK_API_KEY")
    app_id = data.app_id
    country = data.country

    url = f"https://api.apptweak.com/api/v2/applications/{app_id}/competitors.json"
    params = {
        "country": country.lower(),
        "device": "iphone"
    }
    headers = {
        "Authorization": f"Bearer {apptweak_key}"
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
        return { "error": str(e) }
