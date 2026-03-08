# WebSocket Error Handling and Reconnection UX Improvements

## Summary
Enhanced the WebSocket connection handling with better visual indicators, error messages, manual reconnect capability, and a message retry queue.

## Files Changed

### 1. `frontend/src/lib/api/websocket.ts`

**New Features:**
- **Connection State Management**: Added detailed connection states (`connecting`, `connected`, `disconnected`, `reconnecting`, `error`)
- **Message Retry Queue**: Messages sent while disconnected are queued and retried when connection is restored
  - Max queue size: 100 messages
  - Max retries per message: 3
  - Automatic flush on reconnection
- **Exponential Backoff**: Reconnection attempts use exponential backoff (max 30 seconds)
- **Better Error Messages**: Specific error messages for different failure scenarios
- **Manual Reconnect**: New `reconnect()` method for user-triggered reconnection
- **Queue Clearing**: New `clearQueue()` method to clear pending messages

**New Exports:**
- `connectionState` - Store with connection status, error messages, and retry counts
- Enhanced `websocket` store with `reconnect()` and `clearQueue()` methods

**Key Improvements:**
- Connection state synced with UI store automatically
- Better handling of connection lifecycle (prevents duplicate connections)
- Proper cleanup on disconnect
- Improved error logging

### 2. `frontend/src/lib/stores/index.ts`

**Enhancements:**
- Added `wsStatus` field to track detailed connection state
- Added `wsError` field to store current error message
- Added `setWsStatus()` method to update both status and error simultaneously
- `wsConnected` is now automatically set based on `wsStatus`

### 3. `frontend/src/routes/+layout.svelte`

**New UI Components:**

#### Connection Error Banner
- Fixed-position banner at top of screen when connection is in error state
- Shows error message with warning icon
- Provides "Retry Connection" button for immediate retry
- Only shown when a project is loaded

#### Enhanced Sidebar Status Indicator
- **Visual Indicators:**
  - Green dot: Connected
  - Yellow pulsing dot: Connecting/Reconnecting
  - Red dot: Error
  - Gray dot: Disconnected

- **Status Text:** Clear text labels for each state

- **Error Messages:** Display current error in a styled box

- **Reconnection Progress:** Shows attempt count (e.g., "Attempt 3/5")

- **Manual Reconnect Button:** Appears when disconnected or in error state

## User Experience Improvements

### Before
- Simple green/red indicator
- Automatic reconnection with no feedback
- No way to manually retry
- Messages sent while disconnected were lost

### After
- Rich visual status with animations
- Detailed error messages explaining issues
- Clear progress during reconnection attempts
- Manual retry capability
- Messages queued and sent on reconnection
- Non-intrusive sidebar status + prominent error banner

## Technical Details

### Message Queue Behavior
1. When connection is down, messages are added to queue
2. Queue has max size of 100 (oldest dropped when exceeded)
3. On reconnection, queued messages are flushed
4. Failed sends are re-queued with retry count
5. After 3 retries, message is dropped with warning

### Reconnection Strategy
1. Automatic reconnection on unexpected disconnect
2. Exponential backoff: 2s, 4s, 8s, 16s, 30s (max)
3. Max 5 automatic attempts
4. After max attempts, requires manual intervention
5. Manual reconnect resets all counters

### Error Handling
- Connection errors show specific messages
- Parse errors don't break connection
- Network issues trigger reconnection
- Clear error states when connection succeeds

## Testing Recommendations

1. **Disconnect Scenarios:**
   - Kill backend server → Should see error banner
   - Click "Retry Connection" → Should reconnect
   - Send messages while disconnected → Should queue
   - Restart server → Should auto-reconnect and flush queue

2. **UI States:**
   - Verify all status indicators change appropriately
   - Check banner appears/disappears correctly
   - Ensure manual reconnect button works
   - Verify attempt counter shows during reconnection

3. **Message Queue:**
   - Send multiple messages while disconnected
   - Verify they're sent on reconnection
   - Check queue size limits work
   - Verify retry logic for failed sends

## Future Enhancements (Not Implemented)

- Toast notifications for transient errors
- Sound alerts for critical connection issues
- Connection statistics (latency, uptime)
- Message queue viewer
- Offline mode with local storage
