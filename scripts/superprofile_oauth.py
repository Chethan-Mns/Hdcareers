#!/usr/bin/env python3
"""One-time SuperProfile CI OAuth consent and encrypted rotating refresh tokens.

First-time setup (run locally; never paste keys or tokens in ChatGPT):
  python scripts/superprofile_oauth.py connect
  # Add printed SUPERPROFILE_FERNET_KEY to GitHub Actions repository secrets.
  # Commit ONLY data/integrations/superprofile-oauth.enc.json (encrypted).

Daily CI:
  python scripts/superprofile_oauth.py refresh --access-file /tmp/superprofile-token
  # CI commits rotated encrypted refresh token BEFORE delivery.

Uses official OAuth metadata, dynamic client registration, PKCE (S256),
refresh-token rotation and exact MCP resource audience.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlencode,urlparse
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

from cryptography.fernet import Fernet,InvalidToken

OAUTH_METADATA="https://mcp.superprofile.bio/.well-known/oauth-authorization-server"
RESOURCE="https://mcp.superprofile.bio/mcp"
STORE=Path("data/integrations/superprofile-oauth.enc.json")
SCOPE="accounts:read instagram_schedule:read instagram_schedule:write instagram_schedule:publish autodm:read autodm:write autodm:activate"


def req_json(url:str,payload:dict|None=None, *,form=False)->dict:
    if payload is None:data=None
    elif form:data=urlencode(payload).encode("utf-8")
    else:data=json.dumps(payload).encode("utf-8")
    headers={"Accept":"application/json"}
    if payload is not None:headers["Content-Type"]="application/x-www-form-urlencoded" if form else "application/json"
    try:
        with urlopen(Request(url,data=data,headers=headers,
                             method="POST" if data is not None else "GET"),timeout=35) as response:
            return json.load(response)
    except HTTPError as e:
        raise RuntimeError(f"SuperProfile OAuth HTTP {e.code}; consent/token rejected") from None


def pack(state:dict,key:bytes,store:Path):
    cipher=Fernet(key).encrypt(json.dumps(state,separators=(",",":")).encode("utf-8"))
    store.parent.mkdir(parents=True,exist_ok=True)
    tmp=store.with_suffix(".tmp")
    tmp.write_text(json.dumps({"version":1,"ciphertext":cipher.decode("ascii")})+"\n",encoding="utf-8")
    os.chmod(tmp,0o600)
    os.replace(tmp,store)


def unpack(store:Path,key:bytes)->dict:
    data=json.loads(store.read_text(encoding="utf-8"))
    if data.get("version")!=1:raise RuntimeError("Encrypted OAuth state version unsupported")
    try:return json.loads(Fernet(key).decrypt(data["ciphertext"].encode("ascii")))
    except (InvalidToken,ValueError):raise RuntimeError("Encrypted OAuth state cannot be decrypted") from None


def refresh(store:Path,access_file:Path,*,key:bytes|None=None)->None:
    key=key or os.environ.get("SUPERPROFILE_FERNET_KEY","").encode("ascii")
    if not key:raise RuntimeError("SUPERPROFILE_FERNET_KEY repository secret is missing")
    state=unpack(store,key)
    meta=req_json(OAUTH_METADATA)
    endpoint=str(meta.get("token_endpoint") or state.get("token_endpoint") or "")
    if not endpoint.startswith("https://mcp.superprofile.bio/"):
        raise RuntimeError("Unexpected SuperProfile token endpoint")
    form={"grant_type":"refresh_token","refresh_token":state["refresh_token"],
          "client_id":state["client_id"],"resource":RESOURCE}
    if state.get("client_secret"):form["client_secret"]=state["client_secret"]
    tokens=req_json(endpoint,form,form=True)
    access=tokens.get("access_token")
    rotated=tokens.get("refresh_token")
    if not access or not rotated:raise RuntimeError("SuperProfile did not return rotating tokens")
    updated=dict(state,refresh_token=rotated,token_endpoint=endpoint,updatedAt=int(time.time()))
    # Refresh rotates immediately. Persist ciphertext before any other provider
    # action, then commit it as the next step in GitHub Actions.
    pack(updated,key,store)
    access_file.parent.mkdir(parents=True,exist_ok=True)
    access_file.write_text(access+"\n",encoding="utf-8")
    os.chmod(access_file,0o600)
    print("SuperProfile OAuth refreshed; secret access token kept in temporary file")


def connect(store:Path,port:int):
    # Run on the owner's Mac. The browser authenticates and grants the requested
    # scopes; this script receives only the callback, never their password.
    meta=req_json(OAUTH_METADATA)
    register_url=str(meta.get("registration_endpoint") or "")
    auth_url=str(meta.get("authorization_endpoint") or "")
    token_url=str(meta.get("token_endpoint") or "")
    if not all(u.startswith("https://mcp.superprofile.bio/") for u in [register_url,auth_url,token_url]):
        raise RuntimeError("Unexpected provider OAuth endpoint")
    redirect=f"http://127.0.0.1:{port}/oauth/callback"
    client=req_json(register_url,{
        "client_name":"HD Careers CI Reel Factory",
        "redirect_uris":[redirect],
        "token_endpoint_auth_method":"none",
        "grant_types":["authorization_code","refresh_token"],
        "response_types":["code"]
    })
    client_id=client.get("client_id")
    if not client_id:raise RuntimeError("OAuth dynamic client registration unavailable")
    verifier=secrets.token_urlsafe(65)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state_value=secrets.token_urlsafe(28)
    params={
       "response_type":"code","client_id":client_id,"redirect_uri":redirect,
       "code_challenge_method":"S256","code_challenge":challenge,
       "state":state_value,"scope":SCOPE,"resource":RESOURCE}
    link=auth_url+"?"+urlencode(params)
    received={}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            query=parse_qs(urlparse(self.path).query)
            if urlparse(self.path).path!="/oauth/callback" or query.get("state",[None])[0]!=state_value:
                self.send_error(403);return
            received["code"]=query.get("code",[None])[0]
            received["error"]=query.get("error",[None])[0]
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"SuperProfile authorization received. You can return to the terminal.")
        def log_message(self,*args):pass
    server=HTTPServer(("127.0.0.1",port),Handler)
    server.timeout=2
    print("Opening SuperProfile in the browser for a ONE-TIME GitHub worker connection.")
    print("If browser does not open, use this authorization URL:\n"+link)
    webbrowser.open(link)
    deadline=time.monotonic()+300
    while "code" not in received and "error" not in received and time.monotonic()<deadline:
        server.handle_request()
    server.server_close()
    if received.get("error"):raise RuntimeError("SuperProfile authorization refused")
    if not received.get("code"):raise RuntimeError("OAuth approval not received")
    form={"grant_type":"authorization_code","code":received["code"],
          "client_id":client_id,"redirect_uri":redirect,
          "code_verifier":verifier,"resource":RESOURCE}
    if client.get("client_secret"):form["client_secret"]=client["client_secret"]
    tokens=req_json(token_url,form,form=True)
    if not tokens.get("refresh_token"):raise RuntimeError("No refresh token returned")
    key=Fernet.generate_key()
    pack({"client_id":client_id,"client_secret":client.get("client_secret"),
          "refresh_token":tokens["refresh_token"],
          "token_endpoint":token_url,"updatedAt":int(time.time())},key,store)
    print("\nAuthorization complete. Commit ONLY encrypted file:",store)
    print("Create GitHub Actions secret named SUPERPROFILE_FERNET_KEY with this value:")
    print(key.decode("ascii"))
    print("Never add the key itself to Git or send it through chat.")


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("command",choices=("connect","refresh"))
    ap.add_argument("--store",type=Path,default=STORE)
    ap.add_argument("--access-file",type=Path,default=Path("/tmp/hd-superprofile-token"))
    ap.add_argument("--port",type=int,default=7418)
    args=ap.parse_args()
    if args.command=="connect":connect(args.store,args.port)
    else:refresh(args.store,args.access_file)


if __name__=="__main__":
    main()
