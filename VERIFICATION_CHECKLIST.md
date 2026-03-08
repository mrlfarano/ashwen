# WebSocket Improvements - Verification Checklist

## Manual Testing Steps

### 1. Visual Indicators Test
- [ ] Start the app with backend running
- [ ] Verify green dot shows "Connected"
- [ ] Kill backend server
- [ ] Verify red dot shows "Connection Error"
- [ ] Verify error banner appears at top
- [ ] Restart backend
- [ ] Verify automatic reconnection with yellow pulsing dot
- [ ] Verify returns to green when connected

### 2. Error Messages Test
- [ ] Disconnect backend
- [ ] Verify error message shows in sidebar
- [ ] Verify error message shows in banner
- [ ] Click "Retry Connection" button
- [ ] Verify "Connecting..." state shows
- [ ] Verify error updates appropriately

### 3. Manual Reconnect Test
- [ ] Disconnect backend until max retries reached
- [ ] Verify "Reconnect" button appears in sidebar
- [ ] Verify "Retry Connection" button in banner
- [ ] Restart backend
- [ ] Click either reconnect button
- [ ] Verify connection is re-established

### 4. Message Queue Test
- [ ] Disconnect backend
- [ ] Send multiple chat messages
- [ ] Verify "Message queued" notification appears
- [ ] Restart backend
- [ ] Wait for reconnection
- [ ] Verify queued messages are sent
- [ ] Verify no messages were lost

### 5. Reconnection Progress Test
- [ ] Disconnect backend
- [ ] Watch sidebar for attempt counter
- [ ] Verify shows "Attempt X/5"
- [ ] Verify delay increases between attempts
- [ ] Verify max attempts shows error state

### 6. Edge Cases
- [ ] Try to reconnect without project selected
- [ ] Rapidly disconnect/reconnect multiple times
- [ ] Send 100+ messages while disconnected (verify queue limit)
- [ ] Refresh page during reconnection

## Expected Behaviors

### Connection States
- **Connected**: Green dot, "Connected", no error message
- **Connecting**: Yellow pulsing dot, "Connecting..."
- **Reconnecting**: Yellow pulsing dot, "Reconnecting...", shows attempt count
- **Disconnected**: Gray dot, "Disconnected", shows reconnect button
- **Error**: Red dot, "Connection Error", shows error message and reconnect button

### Message Queue
- Messages queue when connection is not OPEN
- Queue max size: 100 messages
- Max retries per message: 3
- Queue flushes automatically on reconnection
- Failed messages get re-queued with retry count

### Reconnection
- Automatic reconnection on unexpected disconnect
- Exponential backoff: 2s, 4s, 8s, 16s, 30s (max)
- Max 5 automatic attempts
- Manual reconnect available after max attempts
- Manual reconnect resets all counters

## Files to Review
- ✅ `frontend/src/lib/api/websocket.ts` - Enhanced connection handling
- ✅ `frontend/src/lib/stores/index.ts` - Extended UI store
- ✅ `frontend/src/routes/+layout.svelte` - New UI components

## Implementation Notes
- Connection state is synced between websocket.ts and UI store
- Error banner only shows when a project is loaded
- Message queue prevents data loss during disconnection
- Exponential backoff prevents server hammering
- Visual feedback keeps user informed at all times
