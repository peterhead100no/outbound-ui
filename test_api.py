#!/usr/bin/env python3
"""
Simple test to check if the API calls are working
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

EXOTEL_API_KEY = os.getenv("EXOTEL_API_KEY")
EXOTEL_API_TOKEN = os.getenv("EXOTEL_API_TOKEN")
EXOTEL_SUBDOMAIN = os.getenv("EXOTEL_SUBDOMAIN", "api.exotel.in")
EXOTEL_SID = os.getenv("EXOTEL_SID")

print("=" * 70)
print("EXOTEL API CONNECTION TEST")
print("=" * 70)

print(f"\n✓ EXOTEL_API_KEY: {EXOTEL_API_KEY[:20]}..." if EXOTEL_API_KEY else "✗ EXOTEL_API_KEY: NOT SET")
print(f"✓ EXOTEL_API_TOKEN: {EXOTEL_API_TOKEN[:20]}..." if EXOTEL_API_TOKEN else "✗ EXOTEL_API_TOKEN: NOT SET")
print(f"✓ EXOTEL_SUBDOMAIN: {EXOTEL_SUBDOMAIN}")
print(f"✓ EXOTEL_SID: {EXOTEL_SID}")

if not all([EXOTEL_API_KEY, EXOTEL_API_TOKEN, EXOTEL_SID]):
    print("\n❌ Missing required environment variables!")
    sys.exit(1)

print("\n" + "=" * 70)
print("STEP 1: Testing API Credentials Format")
print("=" * 70)

# Test URL format
test_call_sid = "test123456789012345678901234567890"
url = f"https://{EXOTEL_API_KEY}:{EXOTEL_API_TOKEN}@{EXOTEL_SUBDOMAIN}/v1/Accounts/{EXOTEL_SID}/Calls/{test_call_sid}?details=true"
print(f"\nURL Format (masked):")
print(f"https://***:***@{EXOTEL_SUBDOMAIN}/v1/Accounts/{EXOTEL_SID}/Calls/{test_call_sid}?details=true")

print("\n" + "=" * 70)
print("STEP 2: Testing actual API call with a REAL call_sid")
print("=" * 70)

import requests

call_sid_input = input("\n📞 Enter a REAL call_sid from a recent successful dial (or press Enter to skip): ").strip()

if call_sid_input:
    print(f"\nTesting with call_sid: {call_sid_input}")
    
    url = f"https://{EXOTEL_API_KEY}:{EXOTEL_API_TOKEN}@{EXOTEL_SUBDOMAIN}/v1/Accounts/{EXOTEL_SID}/Calls/{call_sid_input}?details=true"
    
    try:
        print(f"\n🔄 Making request to Exotel API...")
        response = requests.get(url, timeout=10)
        
        print(f"\n✓ Response Status Code: {response.status_code}")
        print(f"✓ Content-Type: {response.headers.get('content-type')}")
        print(f"✓ Response Length: {len(response.text)} characters")
        
        print(f"\n📋 Full Response (first 1000 chars):")
        print(response.text[:1000])
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"\n✅ SUCCESS - Valid JSON Response!")
                print(f"\nCall Details:")
                if "Call" in data:
                    call_data = data["Call"]
                    print(f"  - Status: {call_data.get('Status', 'N/A')}")
                    print(f"  - Duration: {call_data.get('Duration', 'N/A')}")
                    print(f"  - AnsweredBy: {call_data.get('AnsweredBy', 'N/A')}")
                    print(f"  - EndTime: {call_data.get('EndTime', 'N/A')}")
                    print(f"  - Sid: {call_data.get('Sid', 'N/A')}")
                else:
                    print("  ❌ No 'Call' key in response!")
                    print(f"  Available keys: {list(data.keys())}")
            except Exception as e:
                print(f"\n❌ JSON Parse Error: {e}")
        else:
            print(f"\n❌ HTTP Error {response.status_code}")
            print(f"Error Response: {response.text}")
            
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ Connection Error: {e}")
    except requests.exceptions.Timeout as e:
        print(f"\n❌ Timeout Error: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
else:
    print("\nSkipped API testing. Run this script again with a real call_sid to test.")

print("\n" + "=" * 70)
print("DIAGNOSIS COMPLETE")
print("=" * 70)
