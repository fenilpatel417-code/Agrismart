import urllib.request
import urllib.parse
import sys

class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        # Stop redirection, keep the response
        return fp

def test_login(identifier, password):
    url = "http://127.0.0.1:8000/login"
    data = urllib.parse.urlencode({
        "phone": identifier,
        "password": password
    }).encode("utf-8")
    
    opener = urllib.request.build_opener(NoRedirectHandler())
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        response = opener.open(req)
        status = response.status
        headers = response.headers
        location = headers.get("Location")
        set_cookie = headers.get("Set-Cookie")
        
        if status == 302 and location == "/dashboard":
            print(f"[SUCCESS] Login test for '{identifier}': Redirected to {location}")
            if "access_token" in (set_cookie or ""):
                print("         Cookie 'access_token' successfully set!")
            else:
                print("         [WARN] Cookie NOT set.")
            return True
        else:
            print(f"[FAIL] Login test for '{identifier}': Status {status}, Redirected to: {location}")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to connect to server: {e}")
        return False

if __name__ == "__main__":
    print("Testing email login:")
    test_login("admin@agrismart.com", "Admin@123")
    print("\nTesting phone login:")
    test_login("7016998037", "Admin@123")
