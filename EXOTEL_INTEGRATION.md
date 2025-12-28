# Exotel Call Status Integration

## Overview
The app now tracks and monitors call status using Exotel API's Call SID (Session ID). After each dial, the app stores the SID and can poll the Exotel API to get real-time call status.

## Key Features Added

### 1. **SID Extraction & Storage**
- When a call is initiated, the app extracts the `Sid` from the API response
- The SID is stored in `session_state.call_status[idx]['sid']`

### 2. **Real-time Status Polling**
- `get_call_status()` function fetches the latest call status using the SID
- Returns: Status, Duration, AnsweredBy, EndTime

### 3. **Manual Mode Enhancements**
- **Refresh Status Button**: Manually refresh all pending call statuses
- **Check Status Button**: Check individual call status on-demand
- **Status Display**: Shows duration, end time, and caller information

### 4. **Automatic Mode Enhancements**
- **Auto-refresh Toggle**: Checkbox to auto-refresh every 10 seconds
- **Real-time Updates**: Status updates automatically without manual intervention
- **Progress Tracking**: Shows SID and duration in the status table

## Configuration

### Environment Variables
Add these to your `.env` file:

```env
EXOTEL_API_KEY=your_api_key
EXOTEL_API_TOKEN=your_api_token
EXOTEL_SUBDOMAIN=your_subdomain
EXOTEL_SID=Exotel
```

### API Endpoint Format
```
https://<api_key>:<api_token>@<subdomain>/v1/Accounts/<sid>/Calls/<CallSid>
```

## Usage

### Manual Mode
1. Upload Excel file with contact details
2. Click "📞 Dial" to initiate a call
3. Click "🔄 Refresh Status" to refresh all calls
4. Click "🔍 Check Status" on individual calls for immediate status

### Automatic Mode
1. Configure interval and batch size
2. Click "▶️ Start Automatic Dialing"
3. Enable "🔄 Auto-refresh every 10s" for continuous status updates
4. Status updates every 10 seconds automatically

## Response Format
The app expects the following response format from Exotel API:

```json
{
  "Call": {
    "Sid": "80bfbec2d78bbbf10fb851f4fa165211",
    "Status": "in-progress",
    "Duration": 45,
    "AnsweredBy": "human",
    "EndTime": "2017-03-03 12:30:27"
  }
}
```

## Status Values
- `in-progress`: Call is active
- `completed`: Call has ended
- `no-answer`: Call was not answered
- `failed`: Call failed to connect

## Data Structure

### Call Status Object
```python
{
    'status': 'Dialed' | 'Failed' | 'in-progress' | 'completed',
    'timestamp': '12:30:45',  # When the call was initiated
    'error': None,  # Error message if failed
    'sid': 'call_sid_value',  # Exotel Call SID
    'duration': 45,  # Duration in seconds
    'answered_by': 'human',  # Who answered
    'end_time': '2017-03-03 12:30:27'  # When call ended
}
```

## Display Features

### Status Table Columns
- **Name**: Contact name
- **Phone No**: Phone number
- **Reason**: Reason of call
- **Status**: Current call status
- **SID**: First 12 characters of Call SID
- **Duration (s)**: Call duration in seconds
- **Time**: Call initiation time
- **Error**: Error message if applicable

## Functions

### `dial_number(phone_number)`
- Makes API call to initiate a call
- **Returns**: `(success: bool, message: str, sid: str)`
- Extracts and returns the SID from response

### `get_call_status(sid)`
- Fetches current call status from Exotel API
- **Returns**: `(success: bool, status: str, details: dict)`
- Details include: status, duration, answered_by, end_time

## Error Handling
- Timeout errors: "Request timeout"
- Connection errors: "Connection error"
- Invalid responses: Graceful fallback with error messages
- Missing SID: Call marked as "Failed"

## Polling Strategy

### Manual Refresh (Manual Mode)
- Click "🔄 Refresh Status" button to fetch latest status for all calls

### Auto-refresh (Automatic Mode)
- Enable "🔄 Auto-refresh every 10s" checkbox
- Status updates automatically every 10 seconds
- Only checks calls with valid SID and status of 'Dialed' or 'in-progress'

## Notes
- Always add Exotel API credentials to `.env` before running
- The app uses environment variables for security
- Default SID is 'Exotel' if not specified
- Status is only polled for calls with a valid SID
