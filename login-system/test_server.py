"""測試服務器連接的腳本"""
import requests
import sys
import time

def test_server(port=5000, max_attempts=10):
    """測試服務器是否正常運行"""
    url = f"http://127.0.0.1:{port}"
    print(f"Testing connection to {url}...")
    
    for i in range(max_attempts):
        try:
            response = requests.get(url, timeout=2)
            print(f"✓ Server is running! Status: {response.status_code}")
            print(f"✓ Response received from {url}")
            return True
        except requests.exceptions.ConnectionError:
            print(f"Attempt {i+1}/{max_attempts}: Connection refused, waiting...")
            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    print(f"✗ Could not connect to {url}")
    print("Make sure the server is running with: python app.py")
    return False

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    test_server(port)

