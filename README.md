# OpenRouter Fixed for Home Assistant

A comprehensive fix for the OpenRouter integration that adds AI Task entity support with vision capabilities for camera snapshot analysis and structured data generation.

## 🎯 Key Features

- **🤖 AI Task Entity Support**: Full `ai_task.generate_data` service integration
- **📷 Camera Snapshot Analysis**: Direct camera feed processing with vision models
- **🔧 OpenAI Library Compatibility**: Works with all OpenAI library versions (1.x and 2.x)
- **📊 Structured Data Output**: JSON responses for automation workflows
- **💰 Free Model Support**: Access to Qwen2.5-VL-72B and other free vision models
- **✅ Home Assistant 2024.12+**: Compatible with latest HA versions
- **🌍 200+ Models**: Access to all OpenRouter models including vision capabilities

## Installation

### Via HACS (Recommended)

1. Install [HACS](https://hacs.xyz/) if you haven't already
2. Add this repository as a custom repository:
   - Go to HACS → Integrations
   - Click the three dots menu → Custom repositories
   - Add: `https://github.com/brouwerict/open_router_fixed`
   - Category: Integration
3. Search for "OpenRouter Fixed" and install it
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/openrouter_fixed` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "OpenRouter Fixed"
4. Enter your OpenRouter API key (get one at [OpenRouter.ai](https://openrouter.ai/))
5. Configure AI Task entities and/or Conversation agents

## 📷 Camera Snapshot Analysis

This integration fully supports image analysis through AI Tasks, perfect for security, vehicle detection, and home monitoring.

### Supported Vision Models

#### Free Models (No cost!)
- `qwen/qwen2.5-vl-72b-instruct:free` - Excellent 72B vision model
- `qwen/qwen2.5-vl-32b-instruct:free` - Good balance of speed/quality

#### Premium Models
- `anthropic/claude-3-haiku` - Fast & cost-effective ($0.25/1M tokens)
- `anthropic/claude-3-5-sonnet` - High accuracy vision
- `openai/gpt-4o-mini` - OpenAI's efficient vision model
- `openai/gpt-4o` - Top-tier OpenAI vision
- `google/gemini-pro-vision` - Google's vision model

### Basic Usage Example

```yaml
# Vehicle detection automation
automation:
  - alias: "Detect Vehicles on Driveway"
    trigger:
      - platform: state
        entity_id: binary_sensor.driveway_motion
        to: 'on'
    action:
      - service: ai_task.generate_data
        data:
          entity_id: ai_task.qwen_qwen2_5_vl_72b_instruct  # Free model!
          task_name: "Vehicle Detection"
          instructions: |
            Analyze this driveway camera image.
            Count all vehicles and return JSON:
            {
              "total_vehicles": 0,
              "total_cars": 0,
              "total_motorcycles": 0,
              "vehicle_list": "Details of detected vehicles"
            }
          attachments:
            media_content_id: media-source://camera/driveway_camera
            media_content_type: image/jpeg
        response_variable: vehicle_data
      
      # Update counters
      - service: input_number.set_value
        target:
          entity_id: input_number.car_count
        data:
          value: "{{ (vehicle_data.data | from_json).total_cars }}"
```

### Advanced Structured Output

```yaml
# Security monitoring with structured data
- service: ai_task.generate_data
  data:
    entity_id: ai_task.anthropic_claude_3_haiku
    task_name: "Security Analysis"
    instructions: "Analyze security camera for threats"
    structure:
      person_detected:
        description: "Whether a person is visible"
        selector:
          boolean:
        required: true
      person_count:
        description: "Number of people detected"
        selector:
          number:
            min: 0
            max: 10
        required: true
      threat_level:
        description: "Security threat assessment"
        selector:
          select:
            options:
              - "none"
              - "low"
              - "medium"
              - "high"
        required: true
      description:
        description: "Detailed description of the scene"
        selector:
          text:
        required: true
    attachments:
      media_content_id: media-source://camera/front_door
      media_content_type: image/jpeg
  response_variable: security_result
```

### Service Call Format

```yaml
service: ai_task.generate_data
data:
  entity_id: ai_task.model_name  # Your AI Task entity
  task_name: "Task Description"  # Required field
  instructions: "What to analyze"  # Your prompt
  attachments:
    media_content_id: media-source://camera/camera_name  # Camera source
    media_content_type: image/jpeg  # Media type
  structure:  # Optional: Define output structure
    field_name:
      description: "Field description"
      selector:
        type:  # boolean, number, text, etc.
      required: true/false
response_variable: result  # Variable to store response
```

## 🔧 Technical Fixes Implemented

### 1. OpenAI Library Compatibility
**Problem:** `ImportError: cannot import name 'ResponseFormatJSONSchema'`

**Solution:** Dynamic import system with fallbacks for all OpenAI library versions

### 2. AI Task Entity Support
**Problem:** No AI Task entities available in original integration

**Solution:** Complete `AITaskEntity` implementation with attachment support

### 3. Vision Model Access
**Problem:** Vision models filtered out or unavailable

**Solution:** Removed restrictive model filtering, all 200+ models now accessible

### 4. Attachment Processing
**Problem:** Cannot process camera snapshots or images

**Solution:** Multi-format attachment handler supporting:
- Camera media sources
- File paths
- Base64 encoded images
- Binary data

### 5. JSON Response Handling
**Problem:** Inconsistent JSON parsing failures

**Solution:** Robust parsing with graceful fallback to raw text

## 💰 Cost Optimization

| Model | Cost per 1000 calls | Quality | Speed |
|-------|---------------------|---------|-------|
| Qwen2.5-VL-72B | **$0.00** (FREE!) | Excellent | Good |
| Claude 3 Haiku | $0.61 | Good | Fast |
| GPT-4o-mini | $0.42 | Good | Fast |
| Claude 3.5 Sonnet | $7.80 | Excellent | Medium |

**Recommendation:** Use `qwen/qwen2.5-vl-72b-instruct:free` for production - it's completely free and performs excellently!

## 📝 Example Use Cases

### Package Detection
```yaml
- Detect packages at front door
- Notify when delivery arrives
- Log delivery times
```

### Vehicle Monitoring
```yaml
- Count cars in driveway
- Detect unknown vehicles
- Track parking occupancy
```

### Security Surveillance
```yaml
- Person detection
- Threat assessment
- Anomaly detection
```

### Pet Monitoring
```yaml
- Check if pets are inside/outside
- Food bowl monitoring
- Activity tracking
```

## Troubleshooting

### "Bad request to API" Error
- Check entity_id exists in Developer Tools > States
- Verify model name is correct
- Ensure API key has sufficient credits

### JSON Parsing Errors
- Add "Return ONLY valid JSON" to instructions
- Use simpler JSON structure
- Try different model (Qwen models are very consistent)

### Attachment Errors
- Use `media-source://camera/camera_name` format
- Ensure camera entity is available
- Check file permissions for file attachments

## Getting an API Key

1. Visit [OpenRouter.ai](https://openrouter.ai/)
2. Create account
3. Generate API key
4. Add credits (or use free models!)

## Support

For issues or questions, please [open an issue](https://github.com/brouwerict/open_router_fixed/issues) on GitHub.

## Contributing

Pull requests welcome! See [TECHNICAL_PR_DESCRIPTION.md](TECHNICAL_PR_DESCRIPTION.md) for technical details.

## License

Apache 2.0 - Same as Home Assistant

## Credits

- Based on the official OpenRouter integration for Home Assistant
- Enhanced with AI Task support and vision capabilities
- Original author: [@joostlek](https://github.com/joostlek)