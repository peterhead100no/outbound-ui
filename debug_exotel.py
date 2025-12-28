#!/usr/bin/env python3
"""
Debug script to test Exotel API connectivity and status fetch
"""
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

EXOTEL_API_KEY = os.getenv("EXOTEL_API_KEY")
EXOTEL_API_TOKEN = os.getenv("EXOTEL_API_TOKEN")
EXOTEL_SUBDOMAIN = os.getenv("EXOTEL_SUBDOMAIN", "api.exotel.in")
EXOTEL_SID = os.getenv("EXOTEL_SID")

print("=" * 60)
print("EXOTEL API DEBUG TEST")
print("=" * 60)

print(f"\n✓ API Key: {EXOTEL_API_KEY[:10]}..." if EXOTEL_API_KEY else "✗ API Key: NOT SET")
print(f"✓ API Token: {EXOTEL_API_TOKEN[:10]}..." if EXOTEL_API_TOKEN else "✗ API Token: NOT SET")
print(f"✓ Subdomain: {EXOTEL_SUBDOMAIN}")
print(f"✓ SID: {EXOTEL_SID}")

def test_get_call_status(sid):
    """Test fetching call status"""
    print(f"\n\nTesting call status for SID: {sid}")
    print("-" * 60)
    
    url = f"https://{EXOTEL_API_KEY}:{EXOTEL_API_TOKEN}@{EXOTEL_SUBDOMAIN}/v1/Accounts/{EXOTEL_SID}/Calls/{sid}?details=true"
    
    print(f"URL (masked): https://***:***@{EXOTEL_SUBDOMAIN}/v1/Accounts/{EXOTEL_SID}/Calls/{sid}?details=true")
    
    try:
        response = requests.get(url, timeout=10, verify=True)
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ SUCCESS - Response received:")
            print(f"   Call Status: {data.get('Call', {}).get('Status')}")
            print(f"   Duration: {data.get('Call', {}).get('Duration')}")
            print(f"   AnsweredBy: {data.get('Call', {}).get('AnsweredBy')}")
            print(f"   EndTime: {data.get('Call', {}).get('EndTime')}")
            print(f"\nFull Response:\n{data}")
        else:
            print(f"\n❌ ERROR - Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ CONNECTION ERROR: {str(e)}")
    except requests.exceptions.Timeout as e:
        print(f"\n❌ TIMEOUT ERROR: {str(e)}")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")

# Test with a sample SID
if __name__ == "__main__":
    sid = input("\nEnter a Call SID to test (or press Enter to skip): ").strip()
    
    if sid:
        test_get_call_status(sid)
    else:
        print("\nNo SID provided. Exiting...")
    
    print("\n" + "=" * 60)
