# OpenRouter Fixed - Release v1.2.6

## 🎯 Feature Release: Improved API Error Handling & Automatic Retries

This release dramatically improves error handling with specific, actionable error messages and automatic retry logic for transient API failures.

## ✨ What's New

### **Intelligent Error Handling** (Major Improvement)

**Before**: Generic unhelpful error messages
```
Error talking to API
```

**After**: Specific, actionable error messages with provider context
```
Provider 'Chutes' is temporarily at capacity. Please try again in a few minutes or select a different model.
```

### **Automatic Retry Logic** (New Feature)

The integration now automatically retries transient API errors:

| Error Type | Max Retries | Retry Delays | Total Wait |
|------------|-------------|--------------|------------|
| **503** Service Unavailable | 2 | 5s, 10s | Up to 15s |
| **429** Rate Limit | 2 | 10s, 20s | Up to 30s |

**Benefits**:
- ✅ Handles temporary provider capacity issues automatically
- ✅ Reduces failed requests during high load periods
- ✅ No user intervention needed for transient failures
- ✅ Detailed logging shows retry progress

**Example log output**:
```
Provider 'Chutes' temporarily unavailable (attempt 1/3). Retrying in 5s...
Provider 'Chutes' temporarily unavailable (attempt 2/3). Retrying in 10s...
```

## 🔧 Specific Error Types Handled

### **1. 503 Service Unavailable**

**What it means**: Provider (e.g., Chutes) has no available GPU instances

**Old behavior**: Generic error, immediate failure

**New behavior**:
- Automatically retries 2 times (5s, 10s delays)
- Extracts provider name from error metadata
- Final error if retries fail:
  ```
  Provider 'Chutes' is temporarily at capacity. Please try again in a few minutes or select a different model.
  ```

### **2. 429 Rate Limit**

**What it means**: Too many requests to provider's API

**Old behavior**: Generic error, immediate failure

**New behavior**:
- Automatically retries 2 times (10s, 20s delays)
- Parses rate limit details from upstream
- Final error if retries fail:
  ```
  Rate limit exceeded: mistralai/mistral-small-3.2-24b-instruct:free is temporarily rate-limited upstream.
  Please retry shortly, or add your own key to accumulate your rate limits: https://openrouter.ai/settings/integrations.
  Please wait before retrying or upgrade to a paid plan.
  ```

### **3. 404 Image Input Not Supported**

**What it means**: Model doesn't support vision/image inputs

**Old behavior**: Generic BadRequestError

**New behavior**:
- Detects "no endpoints found that support image input"
- Clear error message:
  ```
  Model deepseek/deepseek-chat does not support images. Please configure a vision-capable model
  (e.g., gpt-4-vision-preview, claude-3-haiku, gemini-pro-vision).
  ```

### **4. Other HTTP Errors**

**New behavior**: Extracts status code and error details
```
API error (404): [specific error message]
API error (500): Internal server error
```

## 📋 Technical Details

### Error Response Parsing (entity.py)

The integration now extracts rich error metadata:

```python
# Extracts from error.response.json():
{
  "error": {
    "message": "Provider returned error",
    "code": 503,
    "metadata": {
      "provider_name": "Chutes",  # ← Used in error messages
      "raw": "{...}"              # ← Additional context
    }
  }
}
```

### Exception Hierarchy

New exception handling order (most specific to most generic):

1. **openai.BadRequestError** → Vision/image errors, malformed requests
2. **openai.APIStatusError** → HTTP status codes (503, 429, 404, etc.)
3. **openai.OpenAIError** → Generic fallback (network, auth, etc.)

### Code Changes

**`entity.py:464-567`**
- Added `import asyncio` for retry delays
- Nested retry loop (max 2 retries for transient errors)
- Status code specific handling (503, 429, 404)
- Provider metadata extraction
- Exponential backoff delays
- Detailed logging at each step

## ✅ Result

- ✅ **Better UX**: Users see clear, actionable error messages
- ✅ **Automatic recovery**: Transient errors often resolve without user action
- ✅ **Better debugging**: Logs show which provider failed and why
- ✅ **Graceful degradation**: Permanent errors still fail fast with clear messages

## 🆙 Upgrade Instructions

### From v1.2.5 or earlier:

1. Update via HACS or manually
2. Restart Home Assistant
3. Monitor logs - you'll see new retry messages during temporary outages

**No configuration changes required** - fully backward compatible.

### What to Expect

**During normal operation**: No visible changes, requests work as before

**During provider issues**: You'll see new log messages:
```
WARNING: Provider 'Chutes' temporarily unavailable (attempt 1/3). Retrying in 5s...
WARNING: Provider 'Chutes' temporarily unavailable (attempt 2/3). Retrying in 10s...
INFO: Request succeeded after 1 retry
```

**If retries fail**: Clear error message instead of generic "Error talking to API"

## 🧪 Tested With

- Home Assistant 2024.1+
- Python 3.11, 3.12, 3.13
- OpenAI library 2.0.0+
- python-open-router 0.3.1+

**Tested error scenarios**:
- ✅ 503 Chutes capacity issues (DeepSeek models under load)
- ✅ 429 Rate limits on free tier models
- ✅ 404 Image input not supported errors
- ✅ Network timeouts and connection errors

## 📦 Commits in This Release

- `1a30a2c` - feat: improved API error handling with retry logic

## 🔗 Links

- **Repository**: https://github.com/brouwerict/open_router_fixed
- **Issues**: https://github.com/brouwerict/open_router_fixed/issues
- **Previous Release**: [v1.2.5](https://github.com/brouwerict/open_router_fixed/releases/tag/v1.2.5)

## 📝 Notes

This release focuses on resilience and user experience during API errors. All features from v1.2.5 remain unchanged:
- AI Task entity support
- Camera snapshot analysis
- Vision model compatibility
- Structured JSON responses
- Lazy import pattern (from v1.2.4)
- OpenAI library v2.x support (from v1.2.5)

### Performance Impact

**Minimal** - Retries only occur during actual failures:
- Normal requests: 0 overhead
- Single transient error: +5-10s recovery time (vs immediate failure)
- Persistent errors: +15-30s before final failure (better UX than instant failure)

### Cost Impact

**None** - Retries for 503/429 don't consume API credits (request never reached model)

---

**Recommendation**: All users should upgrade for better reliability during provider capacity issues and clearer error messages.
