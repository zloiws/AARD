import socket
import urllib.request
from urllib.error import URLError, HTTPError

SERVERS = [
    "http://localhost:11434",
    "http://localhost:11434/v1",
    "http://127.0.0.1:11434",
    "http://127.0.0.1:11434/v1",
    "http://10.39.0.101:11434",
    "http://10.39.0.101:11434/v1",
    "http://10.39.0.6:11434",
    "http://10.39.0.6:11434/v1",
]

def check(url, path="/api/tags"):
    full = url.rstrip("/") + path
    try:
        req = urllib.request.Request(full, headers={"User-Agent": "AARD-check/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            code = resp.getcode()
            print(f"{full} -> {code}")
    except HTTPError as e:
        print(f"{full} -> HTTPError {e.code}")
    except URLError as e:
        print(f"{full} -> URLError {e.reason}")
    except socket.timeout:
        print(f"{full} -> timeout")
    except Exception as e:
        print(f"{full} -> error {e}")

if __name__ == "__main__":
    for s in SERVERS:
        check(s, "/api/tags")
        check(s, "/v1/api/tags")

