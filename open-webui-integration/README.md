# CAMEL Discussion - Open WebUI Integration

Complete integration package for connecting CAMEL Multi-Agent Discussion System with Open WebUI.

## 📦 Package Contents

```
open-webui-integration/
├── README.md                          # This file
├── INSTALLATION.md                     # Detailed installation guide
├── camel_discussion_function.py        # Open WebUI Function (main integration)
├── discussion_viewer.html              # Standalone HTML viewer
└── test_integration.py                 # Integration test script
```

## 🎯 Integration Options

### Option 1: Open WebUI Function (Recommended)

**Best for**: Users who want integration directly in Open WebUI chat interface

**Features**:
- ✅ Works within Open WebUI
- ✅ Natural language commands
- ✅ No separate window needed
- ✅ Easy installation via Admin UI

**Installation**: 5 minutes
**See**: `INSTALLATION.md`

### Option 2: Standalone HTML Viewer

**Best for**: Visual monitoring of discussions with rich UI

**Features**:
- ✅ Beautiful visual interface
- ✅ Real-time WebSocket updates
- ✅ Color-coded agent messages
- ✅ Consensus status panel
- ✅ Works in any browser

**Installation**: Just open `discussion_viewer.html`

### Option 3: Both (Recommended for Full Experience)

Use Open WebUI Function for starting discussions, and HTML Viewer for monitoring them visually.

## 🚀 Quick Start

### For Open WebUI Function

1. **Install Function** (5 min)
   ```bash
   # Open in browser
   http://192.168.110.199:8006

   # Go to Admin → Functions → Add Function
   # Paste content of camel_discussion_function.py
   # Configure Valves (API endpoint)
   # Enable the function
   ```

2. **Use It**
   ```
   # In Open WebUI chat:
   start discussion about climate change solutions
   ```

3. **Done!** 🎉

### For HTML Viewer

1. **Open File**
   ```bash
   # Simply open in browser:
   open discussion_viewer.html

   # Or serve it:
   python3 -m http.server 8888
   # Then: http://localhost:8888/discussion_viewer.html
   ```

2. **Create Discussion**
   - Enter topic
   - Select number of agents
   - Click "Start Discussion"

3. **Watch It Live** 🎉

## 📖 Features

### Open WebUI Function

| Feature | Status | Description |
|---------|--------|-------------|
| Create Discussion | ✅ | Natural language: "start discussion about X" |
| Send Messages | ✅ | Guide discussion: "send message: focus on Y" |
| View Status | ✅ | Check progress: "show status" |
| Stop Discussion | ✅ | End early: "stop discussion" |
| List Models | ✅ | See available LLMs: "list models" |
| Real-time Updates | ⏳ | Future: Full WebSocket streaming |

### HTML Viewer

| Feature | Status | Description |
|---------|--------|-------------|
| Create Discussion | ✅ | UI form with options |
| Real-time Messages | ✅ | WebSocket streaming |
| Visual Role Indicators | ✅ | Color-coded by model |
| Consensus Panel | ✅ | Live consensus status |
| Send User Messages | ✅ | Guide discussion |
| Stop Discussion | ✅ | Graceful termination |
| Responsive Design | ✅ | Works on mobile |
| Auto-scroll | ✅ | Follows conversation |

## 🔧 Configuration

### API Endpoints

**Default** (local network):
```
API: http://192.168.110.199:8007
WebSocket: ws://192.168.110.199:8007
```

**To Change**:
- **Open WebUI Function**: Edit Valves in Admin UI
- **HTML Viewer**: Edit `API_BASE` and `WS_BASE` in `<script>` section

### Number of Agents

**Default**: 3 agents

**To Change**:
- **Open WebUI Function**: Edit `DEFAULT_NUM_AGENTS` in Valves
- **HTML Viewer**: Select in dropdown (2-6 agents)

### Discussion Length

**Default**: 15 turns (Open WebUI), 20 turns (HTML Viewer)

**To Change**:
- **Open WebUI Function**: Edit `DEFAULT_MAX_TURNS` in Valves
- **HTML Viewer**: Edit `max_turns` in `createDiscussion()` function

## 📱 Usage Examples

### Example 1: Medical Discussion

**Open WebUI**:
```
start discussion about best treatments for type 2 diabetes
```

**Result**:
- Creates 3 AI agents (e.g., Endocrinologist, Nutritionist, Patient Advocate)
- Agents discuss treatment options
- You can guide: "send message: focus on lifestyle changes"
- Shows consensus when reached

### Example 2: Technical Discussion

**HTML Viewer**:
1. Enter topic: "microservices vs monolithic architecture"
2. Select 4 agents
3. Watch discussion unfold in real-time
4. See color-coded messages by model
5. Consensus panel shows agreement level

### Example 3: Policy Discussion

**Both**:
1. Start in Open WebUI: `start discussion about carbon tax effectiveness`
2. Get discussion ID
3. Open HTML Viewer
4. You can send messages from both interfaces
5. Real-time sync via WebSocket

## 🧪 Testing

### Test Open WebUI Function

```bash
# 1. Check API is running
curl http://192.168.110.199:8007/health

# 2. In Open WebUI, try:
start discussion about artificial intelligence ethics

# 3. Should see:
# - ✅ Creating discussion...
# - 🎭 Discussion Created!
# - List of 3 AI agents
# - Discussion ID
```

### Test HTML Viewer

```bash
# 1. Open discussion_viewer.html in browser
# 2. Enter topic: "test topic for verification"
# 3. Click "Start Discussion"
# 4. Should see:
# - Status: "Connected"
# - Roles section with agent badges
# - Messages appearing in real-time
```

### Run Automated Tests

```bash
python3 test_integration.py
```

This tests:
- API connectivity
- Discussion creation
- Message sending
- WebSocket connection

## 🐛 Troubleshooting

### Function Not Working

**Problem**: "Failed to create discussion"

**Solutions**:
1. Check API is running:
   ```bash
   curl http://192.168.110.199:8007/health
   # Should return: {"status": "healthy"}
   ```

2. Check Valves configuration in Open WebUI
3. Verify network connectivity
4. Check Open WebUI logs:
   ```bash
   docker logs open-webui-prod --tail 50
   ```

### HTML Viewer Not Connecting

**Problem**: WebSocket error or "Error creating discussion"

**Solutions**:
1. Check browser console (F12) for errors
2. Verify API endpoint in HTML file
3. Try direct API test:
   ```bash
   curl -X POST http://192.168.110.199:8007/api/discussions/create \
     -H "Content-Type: application/json" \
     -d '{"topic":"test","num_agents":3,"user_id":"test"}'
   ```

4. Check CORS is enabled in API

### No Real-Time Updates

**Problem**: Messages don't appear automatically

**Solutions**:
1. Check WebSocket endpoint is correct
2. Verify WebSocket connection in Network tab (browser DevTools)
3. Check firewall isn't blocking WebSocket
4. Try with `ws://` not `wss://`

### CORS Errors

**Problem**: Browser console shows CORS error

**Solution**: CAMEL API already has CORS enabled. If still seeing errors:
1. Check API CORS_ORIGINS setting
2. Add your domain to allowed origins
3. Restart API after config change

## 🔒 Security Considerations

### Current Setup (Development)

- ❌ No authentication
- ❌ No rate limiting
- ❌ HTTP only (not HTTPS)
- ✅ Local network only (192.168.110.199)

### For Production

**Required**:
1. Add authentication (JWT tokens)
2. Implement rate limiting
3. Use HTTPS for API
4. Use WSS for WebSocket
5. Validate user permissions
6. Add input sanitization

**To Implement**:
```python
# In Open WebUI Function Valves, add:
API_KEY: str = Field(default="", description="API authentication key")

# Use it:
headers = {"Authorization": f"Bearer {self.valves.API_KEY}"}
```

## 📊 Architecture

```
┌─────────────────────┐
│   Open WebUI        │
│   (Port 8006)       │
└──────────┬──────────┘
           │
           │ HTTP/REST
           │
┌──────────▼──────────┐
│  CAMEL Function     │
│  (Python)           │
└──────────┬──────────┘
           │
           │ HTTP API
           │
┌──────────▼──────────┐       ┌─────────────────┐
│  CAMEL Discussion   │◄──────┤  HTML Viewer    │
│  API (Port 8007)    │  WS   │  (Browser)      │
└──────────┬──────────┘       └─────────────────┘
           │
           │
┌──────────▼──────────┐
│  CAMEL Engine       │
│  (Orchestrator)     │
└──────────┬──────────┘
           │
           │
┌──────────▼──────────┐
│  OpenRouter API     │
│  (LLM Models)       │
└─────────────────────┘
```

## 📝 API Reference

### Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/discussions/create` | POST | Create new discussion |
| `/api/discussions/{id}` | GET | Get discussion status |
| `/api/discussions/{id}/message` | POST | Send user message |
| `/api/discussions/{id}/messages` | GET | Get message history |
| `/api/discussions/{id}/stop` | POST | Stop discussion |
| `/api/models/` | GET | List available models |
| `/ws/discussions/{id}` | WebSocket | Real-time updates |

### WebSocket Messages

**Received from API**:
```json
{
  "type": "agent_message",
  "data": {
    "role_name": "Neurologist",
    "model": "gpt-4",
    "content": "Based on recent studies...",
    "turn_number": 3
  }
}
```

```json
{
  "type": "consensus_update",
  "data": {
    "reached": false,
    "confidence": 0.65,
    "summary": "Agents are converging..."
  }
}
```

```json
{
  "type": "discussion_complete",
  "data": {
    "total_turns": 12,
    "consensus_reached": true,
    "final_summary": "The panel agreed..."
  }
}
```

## 🎨 Customization

### Change Agent Models

**In Open WebUI Function** (`camel_discussion_function.py`):
```python
# Line 62-64, modify model_preferences:
"model_preferences": ["gpt-4-turbo", "claude-3-sonnet", "gemini-flash"]
```

### Change UI Colors

**In HTML Viewer** (`discussion_viewer.html`):
```javascript
// Line 294-298, modify colors object:
const colors = {
    'gpt-4': '#your-color',
    'claude': '#your-color',
    'gemini': '#your-color'
};
```

### Add Custom Commands

**In Open WebUI Function** (`camel_discussion_function.py`):
```python
# In action() method, add:
elif "my custom command" in user_message:
    # Your custom logic here
    return "Custom response"
```

## 📈 Performance

### Metrics

| Operation | Time | Notes |
|-----------|------|-------|
| Create Discussion | 5-10s | Depends on LLM API |
| Send Message | < 1s | Instant delivery |
| WebSocket Message | < 100ms | Real-time |
| Load Messages | < 500ms | 100 messages |

### Limitations

| Limit | Value | Configurable |
|-------|-------|--------------|
| Max Agents | 6 | Yes (Valves) |
| Max Turns | 30 | Yes (Valves) |
| Max Topic Length | 500 chars | No |
| Concurrent Discussions | Unlimited | Rate limit recommended |

## 🔄 Updates & Maintenance

### Updating the Function

1. Edit `camel_discussion_function.py`
2. Go to Open WebUI Admin → Functions
3. Click on CAMEL Discussion function
4. Replace code
5. Save

Changes take effect immediately.

### Updating HTML Viewer

1. Edit `discussion_viewer.html`
2. Save file
3. Refresh browser

No server restart needed.

## 📞 Support

### Issues

- **API Problems**: Check CAMEL Discussion API logs
- **Open WebUI Problems**: Check `docker logs open-webui-prod`
- **Browser Problems**: Check console (F12 → Console tab)

### Logs

**API Logs**:
```bash
# If running with Python:
tail -f /opt/dev/camel-discussion-engine/logs/api.log

# If running with Docker:
docker logs camel-discussion-api
```

**Open WebUI Logs**:
```bash
docker logs open-webui-prod --tail 100 -f
```

## 🎯 Next Steps

1. **Install**: Follow `INSTALLATION.md`
2. **Test**: Try both Open WebUI Function and HTML Viewer
3. **Customize**: Adjust colors, agents, turns to your needs
4. **Secure**: Add authentication before production use
5. **Monitor**: Set up logging and metrics

## 📄 License

This integration is part of the CAMEL Discussion project.

---

**Version**: 1.0.0
**Last Updated**: 2025-10-12
**Compatibility**: Open WebUI 0.3.x+, CAMEL API 1.0.0+
