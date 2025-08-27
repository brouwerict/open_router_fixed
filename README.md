# OpenRouter Fixed for Home Assistant

A fixed version of the OpenRouter integration for Home Assistant that resolves compatibility issues with the official integration.

## Features

- **📷 Image Analysis Support**: Camera snapshots, uploaded images, and visual content analysis
- **🔧 Fixed OpenAI Library Conflicts**: Resolves version conflicts with other integrations
- **🤖 Improved Model Parsing**: Support for new OpenRouter architectures and modalities
- **✅ Home Assistant 2025.8.0+ Compatible**: Works seamlessly with latest versions
- **🤝 Multi-Integration Friendly**: Runs alongside other OpenAI-based integrations

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
4. Enter your OpenRouter API key
5. Configure conversation agents or AI tasks as needed

## 📷 Image Analysis & Camera Snapshots

Deze integratie ondersteunt volledig **image analysis** via AI Tasks, inclusief camera snapshots!

### Ondersteunde Vision Models
Voor image analyse, kies een van deze vision-compatible models:
- `anthropic/claude-3-haiku` (snel & goedkoop)
- `anthropic/claude-3-sonnet` (balans kwaliteit/snelheid)
- `anthropic/claude-3-opus` (hoogste kwaliteit)
- `openai/gpt-4-vision-preview` (alternatief)
- `google/gemini-pro-vision` (Google's vision model)

### Gebruik in Automations/Scripts
```yaml
# Voorbeeld: Analyseer doorbell camera elke beweging
automation:
  - alias: "Analyze Doorbell Motion"
    trigger:
      - platform: state
        entity_id: binary_sensor.doorbell_motion
        to: 'on'
    action:
      - service: ai_task.generate_data
        target:
          entity_id: ai_task.openrouter_fixed_claude_3_haiku
        data:
          prompt: "Beschrijf wat je ziet in deze camera snapshot van mijn voordeur. Is het een persoon, pakketbezorger, dier, of iets anders?"
          attachments:
            - /tmp/doorbell_snapshot.jpg

# Voorbeeld: Tel auto's op parking
automation:
  - alias: "Count Parking Spots"
    trigger:
      - platform: time_pattern
        minutes: "/15"  # Elke 15 minuten
    action:
      - service: camera.snapshot
        target:
          entity_id: camera.parking_lot
        data:
          filename: /tmp/parking_snapshot.jpg
      - service: ai_task.generate_data
        target:
          entity_id: ai_task.openrouter_fixed_claude_3_sonnet
        data:
          prompt: "Tel het aantal geparkeerde auto's op deze parkeerplaats. Return alleen het nummer."
          attachments:
            - /tmp/parking_snapshot.jpg
```

### Structured Data Output
```yaml
# Voorbeeld: Gestructureerde output voor object detection
- service: ai_task.generate_data
  target:
    entity_id: ai_task.openrouter_fixed_claude_3_haiku
  data:
    prompt: "Analyseer deze beveiligingscamera snapshot"
    attachments:
      - /config/www/security_snapshot.jpg
    structure:
      person_detected: bool
      person_count: int  
      description: str
      confidence: str
```

## Getting an API Key

1. Visit [OpenRouter](https://openrouter.ai/)
2. Sign up for an account
3. Generate an API key from your dashboard
4. Add credits to your account for API usage

## Technische Fixes

Deze custom component lost de volgende specifieke problemen op:

### 1. OpenAI Library Import Compatibility (Issue #150165)
**Probleem:** `ImportError: cannot import name 'ResponseFormatJSONSchema' from 'openai.types.shared_params'`

**Oorzaak:** Andere Home Assistant integraties (zoals Extended OpenAI Conversation) installeren verschillende versies van de OpenAI library die incompatibel zijn.

**Oplossing:** 
- Try/except block toegevoegd voor ResponseFormatJSONSchema import in `entity.py`
- Fallback implementatie wanneer de nieuwe types niet beschikbaar zijn
- Flexibele versie requirements (`openai>=1.99.5,<2.0.0`) in manifest.json

### 2. Model Parsing Errors (Issue #149905)
**Probleem:** `'audio' is not a valid Modality` en andere parsing errors bij nieuwe OpenRouter models

**Oorzaak:** OpenRouter API retourneert nieuwe model architectures en modalities die niet herkend worden door de python-open-router library.

**Oplossing:**
- Robuuste error handling in `config_flow.py` _get_models() functie
- Fallback naar directe API calls met safe parsing wanneer de library faalt
- Skip individuele models die niet geparsed kunnen worden zonder de hele integratie te laten crashen

### 3. Image/Attachment Support (Nieuwe Feature!)
**Toevoeging:** Volledige ondersteuning voor camera snapshots en image analysis via AI tasks

**Implementatie:**
- Base64 image encoding voor OpenRouter vision models in `entity.py`
- Multi-part message support met text + images 
- Error handling voor image processing failures
- Vision model validation en helpful error messages
- Support voor alle image formaten (JPEG, PNG, WebP, etc.)

### 4. Verbeterde Error Recovery
- Non-blocking model parsing errors in `__init__.py`
- Betere logging voor debugging
- Graceful degradation wanneer sommige models niet kunnen worden geladen
- Vision model compatibility checking

## Issues Resolved

- [#150165](https://github.com/home-assistant/core/issues/150165): Configuration error after setup
- [#149905](https://github.com/home-assistant/core/issues/149905): Unexpected error when adding features  
- [#150294](https://github.com/home-assistant/core/issues/150294): AI Tasks failing with API errors
- **NEW**: Camera snapshot/image attachment support for AI vision tasks
- **NEW**: Vision model validation and helpful error messages

## Support

For issues or questions, please [open an issue](https://github.com/brouwerict/open_router_fixed/issues) on GitHub.

## Credits

Based on the official OpenRouter integration by [@joostlek](https://github.com/joostlek) for Home Assistant.