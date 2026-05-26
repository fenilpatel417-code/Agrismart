import urllib.request
import json
import sys

def test_endpoint(url):
    print(f"Fetching {url}...")
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req) as response:
            status = response.status
            data = response.read()
            print(f"[SUCCESS] Status: {status} | Length of response: {len(data)} bytes")
            # Try to parse as JSON
            parsed = json.loads(data.decode("utf-8"))
            if isinstance(parsed, dict):
                print(f"          Parsed successfully! Keys: {list(parsed.keys())[:5]}... (Total keys: {len(parsed)})")
            elif isinstance(parsed, list):
                print(f"          Parsed successfully! List length: {len(parsed)} items. First item: {parsed[0] if parsed else 'None'}")
            return True
    except urllib.error.HTTPError as e:
        print(f"[HTTP ERROR] {e.code} - {e.reason}")
        # Try to read error body
        try:
            err_data = e.read().decode("utf-8")
            print(f"             Error Response: {err_data}")
        except Exception:
            pass
        return False
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
        return False

if __name__ == "__main__":
    print("=== TESTING WEATHER API ===")
    test_endpoint("http://127.0.0.1:8000/api/weather")
    print("\n=== TESTING MANDI API ===")
    test_endpoint("http://127.0.0.1:8000/api/mandi")
