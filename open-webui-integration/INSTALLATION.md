# CAMEL Discussion - Open WebUI Installation Guide

## 📋 Prerequisites

1. **CAMEL Discussion API** running on http://192.168.110.199:8007
2. **Open WebUI** deployed at http://192.168.110.199:8006
3. Admin access to Open WebUI

## 🚀 Installation Steps

### Step 1: Access Open WebUI Admin Panel

1. Open browser: `http://192.168.110.199:8006`
2. Login as admin
3. Click your profile icon (top right)
4. Select **"Admin Panel"**

### Step 2: Navigate to Functions

1. In Admin Panel, click **"Functions"** in the left sidebar
2. You'll see the Functions management page

### Step 3: Add CAMEL Discussion Function

1. Click **"+ Add Function"** button (top right)
2. You'll see a code editor

3. **Copy the entire content** of `camel_discussion_function.py`
4. **Paste it** into the code editor

5. Click **"Save"** button

### Step 4: Configure API Endpoint

1. After saving, you'll see the function in the Functions list
2. Click on **"CAMEL Multi-Agent Discussion"** function
3. Look for **"Valves"** section (configuration)
4. Set the following values:

   ```
   API_ENDPOINT: http://192.168.110.199:8007
   WEBSOCKET_ENDPOINT: ws://192.168.110.199:8007
   DEFAULT_NUM_AGENTS: 3
   DEFAULT_MAX_TURNS: 15
   SHOW_THINKING: true
   AUTO_SUMMARIZE: true
   ```

5. Click **"Save Valves"**

### Step 5: Enable the Function

1. Make sure the toggle switch is **ON** (green)
2. The function is now active!

## ✅ Verification

### Test the Function

1. Go to Open WebUI main chat interface
2. Start a new chat
3. Type: **"start discussion about climate change solutions"**
4. You should see:
   - ✅ "🎭 Creating discussion with 3 AI agents..."
   - ✅ List of AI agents created
   - ✅ "Discussion started successfully"

### Expected Output

```
### 🎭 Discussion Created!

**Topic**: climate change solutions

**Agents**:
  • Climate Scientist (gpt-4): Expert in climate science and modeling
  • Policy Expert (claude-3-opus): International climate policy and regulations
  • Engineer (gemini-pro): Renewable energy and green technology

**Discussion ID**: disc_abc123

The AI agents are now discussing. Messages will appear below in real-time.
```

## 📖 Usage

### Creating a Discussion

```
start discussion about [your topic here]
```

**Examples**:
- `start discussion about artificial intelligence ethics`
- `start discussion about quantum computing applications`
- `start discussion about sustainable agriculture`

### Sending Messages to Discussion

```
send message: [your message here]
```

**Example**:
```
send message: Please focus on near-term solutions that are economically viable
```

### Checking Discussion Status

```
show status
```

This shows:
- Current turn number
- Consensus status
- Recent messages
- Agent activity

### Stopping Discussion

```
stop discussion
```

### Listing Available Models

```
list models
```

Shows all LLM models available for discussions.

## 🔧 Troubleshooting

### Function Not Appearing

**Problem**: Function doesn't show up after installation

**Solution**:
1. Check if function was saved successfully
2. Refresh Open WebUI page
3. Make sure you're logged in as admin
4. Check browser console for errors

### API Connection Error

**Problem**: "Failed to create discussion" error

**Solution**:
1. Verify CAMEL API is running:
   ```bash
   curl http://192.168.110.199:8007/health
   ```

2. Check API endpoint in Valves configuration
3. Ensure network connectivity between Open WebUI and API

### Timeout Errors

**Problem**: Requests timeout

**Solution**:
1. Check if CAMEL API is responsive
2. Increase timeout in Valves if needed
3. Check server logs:
   ```bash
   docker logs open-webui-prod --tail 50
   ```

### No Real-Time Updates

**Problem**: Messages don't appear automatically

**Solution**:
1. WebSocket may not be working
2. Check WebSocket endpoint in Valves
3. Currently, need to manually check status with `show status`
4. Full real-time streaming requires custom frontend component

## 🎨 Advanced: Custom UI Component (Optional)

For real-time message streaming with visual interface, see:
`discussion_viewer.html` in this directory

To use:
1. Host the HTML file on a web server
2. Open it in browser
3. It connects directly to CAMEL API WebSocket
4. Provides rich UI for discussions

## 📊 API Endpoints Used

The function uses these CAMEL Discussion API endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/discussions/create` | POST | Create discussion |
| `/api/discussions/{id}` | GET | Get status |
| `/api/discussions/{id}/message` | POST | Send message |
| `/api/discussions/{id}/messages` | GET | Get messages |
| `/api/discussions/{id}/stop` | POST | Stop discussion |
| `/api/models/` | GET | List models |

## 🔒 Security Notes

1. **API Endpoint**: Currently set to local network IP (192.168.110.199)
2. **No Authentication**: Function uses anonymous user ID
3. **Rate Limiting**: None implemented yet

**For Production**:
- Add authentication token
- Implement rate limiting
- Use HTTPS endpoints
- Validate user permissions

## 📝 Configuration Reference

### Valves Explained

| Valve | Default | Description |
|-------|---------|-------------|
| API_ENDPOINT | http://192.168.110.199:8007 | CAMEL API base URL |
| WEBSOCKET_ENDPOINT | ws://192.168.110.199:8007 | WebSocket base URL |
| DEFAULT_NUM_AGENTS | 3 | Number of AI agents (2-6) |
| DEFAULT_MAX_TURNS | 15 | Max discussion turns (3-30) |
| SHOW_THINKING | true | Show agent reasoning |
| AUTO_SUMMARIZE | true | Auto-summarize on consensus |

### Customizing Defaults

To change defaults:
1. Go to Function settings
2. Edit Valves
3. Change values
4. Save

**Example**: For deeper discussions, increase:
```
DEFAULT_NUM_AGENTS: 5
DEFAULT_MAX_TURNS: 25
```

## 🚀 Next Steps

1. **Try it out**: Create your first discussion
2. **Experiment**: Try different topics
3. **Guide discussions**: Send messages to influence direction
4. **Review results**: Check status to see consensus

## 📞 Support

- **API Issues**: Check `/opt/dev/camel-discussion-engine/` logs
- **Open WebUI Issues**: Check `docker logs open-webui-prod`
- **Function Code**: See `camel_discussion_function.py`

---

**Installation Date**: 2025-10-12
**Version**: 1.0.0
**Compatibility**: Open WebUI 0.3.x+
