import os
import requests
from pathlib import Path
from config import WIKI_API, WIKI_PASS, WIKI_UA, WIKI_USER
from dotenv import load_dotenv

load_dotenv()

def get_login_token():
    """
    Requests a login token from wiki to log onto account for uploading.
    """
    s = requests.Session()

    if not WIKI_API:
        raise ValueError("WIKI_API not set!")

    s.headers["User-Agent"] = WIKI_UA

    params = {
        "action": "query",
        "meta": "tokens",
        "type": "login",
        "format": "json",
    }

    r = s.get(WIKI_API, params=params, timeout=20)
    r.raise_for_status()

    resp_json = r.json()

    if "error" in resp_json:
        raise RuntimeError(f'{resp_json["error"]["code"]}: {resp_json["error"]["info"]}')

    token = resp_json["query"]["tokens"]["logintoken"]
    return token, s  # return session too (useful for Step 3 later)

def attempt_login(token, s : requests.sessions.Session):
    """
    Attempts login with given token in the same session.
    """
    if not WIKI_USER:
        raise ValueError("WIKI_USER not set!")
    if not WIKI_PASS:
        raise ValueError("WIKI_PASS not set!")

    data_payload = {
        "action": "login",
        "lgname": WIKI_USER,
        "lgpassword": WIKI_PASS,
        "lgtoken": token,
        "format": "json"
    }

    r = s.post(WIKI_API, data=data_payload, timeout=20)
    r.raise_for_status()
    
    resp_json = r.json()

    if "error" in resp_json:
        raise RuntimeError(f'{resp_json["error"]["code"]}: {resp_json["error"]["info"]}')
    else:
        result = resp_json["login"]["result"]
        if result != "Success":
            reason = resp_json["login"].get("reason", "no reason given")
            raise ValueError(f"Login failed: {result} - {reason}")


def assert_logged_in(s: requests.sessions.Session):
    """
    Make sure login was valid by checking ID and Name.
    """
    params = {
        "action": "query",
        "meta": "userinfo",
        "format": "json"
    }

    ch_resp = s.get(WIKI_API,params=params,timeout=20)
    ch_resp.raise_for_status()

    check_json = ch_resp.json()

    if "error" in check_json:
        raise RuntimeError(f'{check_json["error"]["code"]}: {check_json["error"]["info"]}')
    
    lg_id = check_json["query"]["userinfo"]["id"]
    lg_name = check_json["query"]["userinfo"]["name"]

    if lg_id == 0:
        raise ValueError(f"Not logged in (id = {lg_id}).")
    
    expected_name = WIKI_USER.split("@", 1)[0]
    if lg_name != expected_name:
        raise ValueError(f"Not logged in (name does not match, name = {lg_name}).")


def get_csrf_token(s: requests.sessions.Session):
    """
    After verifying login, ask for csrf token to upload images.
    """
    params = {
        "action": "query",
        "meta": "tokens",
        "type": "csrf",
        "format": "json"
    }

    r = s.get(WIKI_API, params=params, timeout=20)
    r.raise_for_status()

    resp_json = r.json()

    if "error" in resp_json:
        raise RuntimeError(f'{resp_json["error"]["code"]}: {resp_json["error"]["info"]}')
    
    csrf_token = resp_json["query"]["tokens"]["csrftoken"]

    if csrf_token == "+\\":
        raise ValueError(f"Not logged in or anonymous.")

    return csrf_token


def upload_file(s: requests.sessions.Session, csrf_token: str, save_path: Path, wiki_filename: str):
    """
    Uploads a local file to the wiki using the CSRF token from the active session.
    Returns (True, None) on success, or (False, warnings) if the wiki returned warnings.
    Raises RuntimeError or ValueError on API errors or unexpected responses.
    """
    data_payload = {
        "action": "upload",
        "filename": wiki_filename,
        "token": csrf_token,
        "format": "json",
        "comment": "Uploaded by LoreSync",
        "assert": "user"
    }

    is_uploaded = False
    with open(save_path, "rb") as f:
        files = {"file": f}

        r = s.post(WIKI_API,data=data_payload,files=files, timeout=60)
        r.raise_for_status()
        resp_json = r.json()

        if "error" in resp_json:
            raise RuntimeError(f'{resp_json["error"]["code"]}: {resp_json["error"]["info"]}')
        
        if "upload" not in resp_json:
            raise ValueError(f"Unexpected upload response: {resp_json}")
        
        uploaded_obj = resp_json["upload"]
        result = uploaded_obj.get("result")
        warnings = uploaded_obj.get("warnings")
        if result == "Success":
            is_uploaded = True
        elif warnings is not None or result == "Warning":
            return is_uploaded, warnings
        else:
            raise ValueError(f"Unexpected upload response: {resp_json}")
        
    
    return is_uploaded, None

# ------------------------ MAIN ----------------------------

if __name__ == "__main__":
    token, s = get_login_token()
    print("Got login token")
    print("Token length:", len(token))
    print("Cookies stored:", bool(s.cookies))

    attempt_login(token, s)
    print("Login was successful!")

    assert_logged_in(s)

    csrf_token = get_csrf_token(s)
    print(len(csrf_token))

    assert_logged_in(s)

    print(WIKI_API)
    uploaded, warnings = upload_file(s, csrf_token, Path("uploads/test_pika.png"), "test_pika.png")
    print(uploaded)
    print(f"Warnings are: {warnings}")

