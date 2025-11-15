# OpenRouter Fixed - Release v1.2.5

## 🔧 Dependency Fix Release: OpenAI Library v2.x Support

This release fixes a critical import error when using OpenAI library version 2.0.0 or higher.

## 🐛 What's Fixed

### **ImportError: NotGivenOr Type Not Found** (Critical)

**Problem**: Home Assistant failed to load the integration with this error:
```
ImportError: cannot import name 'NotGivenOr' from 'openai._types' (/usr/local/lib/python3.13/site-packages/openai/_types.py)
```

**Root Cause**:
- OpenAI library v2.0.0 (released September 2024) removed the internal type `NotGivenOr` from `openai._types`
- Previous version constraint was `openai>=1.99.5,<2.0.0`
- Home Assistant's dependency resolution installed v2.x despite the constraint, causing the import to fail

**Solution**: Updated OpenAI library requirement to officially support v2.x:

#### Changes

**`manifest.json`**
```json
// Before
"requirements": ["openai>=1.99.5,<2.0.0", "python-open-router>=0.3.1"]

// After
"requirements": ["openai>=2.0.0", "python-open-router>=0.3.1"]
```

## ✅ Result

- ✅ Integration loads successfully with OpenAI library v2.0.0+
- ✅ Future-proof for latest OpenAI features
- ✅ All functionality preserved - no breaking changes
- ✅ Existing code already compatible via TYPE_CHECKING guards

## 🔍 Technical Details

### Why This Works

The integration code was already compatible with OpenAI v2.x:

1. **Type-only imports**: All OpenAI types are imported in `TYPE_CHECKING` blocks (not executed at runtime)
   ```python
   if TYPE_CHECKING:
       from openai.types.chat import ChatCompletionMessage
   ```

2. **Runtime import guards**: All runtime imports use try/except for version compatibility
   ```python
   try:
       from openai.types.shared_params import ResponseFormatJSONSchema
   except ImportError:
       ResponseFormatJSONSchema = dict  # Fallback
   ```

3. **No use of removed types**: The integration never used `NotGivenOr` in its code

### OpenAI v2.0.0 Breaking Changes

For reference, key changes in OpenAI library v2.0.0:
- Removed `NotGivenOr` internal type
- Changed `ResponseFunctionToolCallOutputItem.output` type signature
- Introduced `Omittable` type as replacement pattern

None of these affect this integration's functionality.

## 📦 Version Support

| Component | Version Required |
|-----------|------------------|
| Home Assistant | 2024.1+ |
| Python | 3.11, 3.12, 3.13 |
| OpenAI library | **2.0.0+** (latest: 2.8.0) |
| python-open-router | 0.3.1+ |

## 🔄 Upgrade Instructions

### From v1.2.4 or earlier:

1. Update via HACS or manually
2. Restart Home Assistant
3. Verify integration loads without errors

**No configuration changes required** - fully backward compatible.

## 🧪 Tested With

- Home Assistant Core 2024.1+
- Python 3.13 on WSL2
- OpenAI library 2.0.0 - 2.8.0
- python-open-router 0.3.1

## 📦 Commits in This Release

- `6f749b6` - feat: upgrade to openai library v2.x

## 🔗 Links

- **Repository**: https://github.com/brouwerict/open_router_fixed
- **Issues**: https://github.com/brouwerict/open_router_fixed/issues
- **Previous Release**: [v1.2.4](https://github.com/brouwerict/open_router_fixed/releases/tag/v1.2.4)

## 📝 Notes

This is a dependency fix focused on OpenAI library compatibility. All features from v1.2.4 remain unchanged:
- AI Task entity support
- Camera snapshot analysis
- Vision model compatibility
- Structured JSON responses
- Lazy import pattern (from v1.2.4)

---

**Recommendation**: All users should upgrade to ensure compatibility with current OpenAI library versions.
