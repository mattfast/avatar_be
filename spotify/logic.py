import requests
import urllib

from keys import spotify_client_id, spotify_client_secret

def get_access_token():
    try:
        r = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={
                "grant_type": "client_credentials",
                "client_id": spotify_client_id,
                "client_secret": spotify_client_secret
            })
        print(r.status_code)
        
        r_json = r.json()
        print(r_json)
        return r_json["access_token"]
    except Exception as e:
        print("Unable to retrieve auth token")
        print(e)
        return None

def get_entity_id(access_token, q, type):
    try:
        search_params = urllib.parse.urlencode({ "q": q, "type": type })
        r = requests.get(
            f"https://api.spotify.com/v1/search?{search_params}",
            headers={
                "Authorization": f"Bearer {access_token}"
            })
        
        r_json = r.json()
        items = r_json[f"{type}s"]["items"]

        return items[0]["id"]
    except:
        print("Unable to get entity id")
        return None

def parse_recommendations(track):
    return {
        "album_name": track["album"]["name"],
        "artist_names": list(map(lambda y: y["name"], track["artists"])),
        "name": track["name"]
    }

# currently, type must be an artist or track
def get_recommendation(q, type):
    try:
        access_token = get_access_token()
        if access_token is None:
            return None
        
        entity_id = ""
        if type != "genre":
            entity_id = get_entity_id(access_token, q, type)
            if entity_id is None:
                return None
        else:
            entity_id = q

        type_string = f"seed_{type}s"
        search_params = urllib.parse.urlencode({ type_string: entity_id })

        r = requests.get(
            f"https://api.spotify.com/v1/recommendations?{search_params}",
            headers={
                "Authorization": f"Bearer {access_token}"
            })
        
        r_json = r.json()
        tracks = r_json["tracks"]
        print(tracks)
        top_recs = list(map(parse_recommendations, tracks[:3]))
        
        return top_recs

    except:
        print("Unable to generate recommendations")
        return None




    
