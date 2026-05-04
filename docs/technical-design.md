# Technical Design Document: Voice AI Home Appliance Diagnostic Agent

## Goals
- Build a practical inbound voice agent for appliance diagnostics.
- Maintain conversational memory so callers are not asked for repeated data.
- Schedule technicians by matching ZIP, specialty, and time-slot availability.
- Support visual diagnosis via image upload and vision model analysis.

## Architecture
- **Telephony**: Twilio Voice webhook posts call events and speech transcripts to FastAPI routes.
- **Backend**: FastAPI handles call orchestration, troubleshooting flow, and booking logic.
- **Persistence**: PostgreSQL stores technician data, availability, appointments, and per-call session state.
- **LLM/Vision**: OpenAI Responses API is used for appliance extraction and uploaded image diagnostics.
- **Containerization**: Docker Compose runs API and database with one command.

## Core Runtime Flow
1. Twilio sends inbound call to `/voice/incoming`.
2. Agent greets caller and asks for appliance type.
3. `/voice/respond` advances a state-machine stored in `call_sessions` table:
   - collect appliance, symptom, time started, error code, unusual sounds
   - optionally request customer email for photo upload link
   - run appliance-specific troubleshooting steps
   - if unresolved, collect ZIP and preferred time window
4. Scheduler finds first matching slot using:
   - technician covers ZIP
   - technician has appliance specialty
   - slot is not booked and matches time window
5. Agent confirms and books appointment atomically.
6. If customer uploads image, vision output is stored and used to improve troubleshooting context.

## Database Design
- `technicians`: profile and employment details
- `technician_service_areas`: ZIP coverage by technician
- `technician_specialties`: appliance types by technician
- `technician_availability`: start/end time and booking state
- `appointments`: confirmed booking details
- `call_sessions`: live conversation memory for each call
- `image_uploads`: uploaded file metadata and vision interpretation

## Tradeoffs
- Deterministic business operations (booking, matching, confirmation) remain server-controlled for safety and idempotency.
- LLM is used for narrow, high-value tasks (NLU extraction and image analysis) to reduce hallucination risk.
- TwiML gather loop is used for speed of implementation. For lower latency and barge-in behavior, migrate to Twilio Media Streams + streaming STT/TTS.

## Tier 3 Implementation
- `/media/upload/{token}` serves an upload page and accepts image files.
- Upload token is generated per call and emailed to customer.
- Vision model returns detected appliance, visible issues, and recommended next step.
- Analysis summary is linked to the call session and injected into troubleshooting prompts.
