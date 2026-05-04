# SHS Voice AI Home Appliance Diagnostic Agent

End-to-end inbound voice agent for Sears Home Services assessment (Tier 1 + Tier 2 + Tier 3).

## What Is Implemented
- Inbound call handling via Twilio voice webhooks.
- Conversational diagnostic flow for appliance issues.
- Conversation memory persisted per call session.
- Technician scheduling with ZIP/specialty/time-window matching.
- Appointment confirmation and slot reservation.
- LLM-assisted appliance extraction (OpenAI, with deterministic fallback).
- Tier 3 photo upload link flow + vision analysis endpoint.
- Docker Compose deployment with PostgreSQL + FastAPI.
- Seeded sample technician data (6 technicians, multiple ZIPs/specialties/slots).

## Stack
- FastAPI (Python backend)
- Twilio Programmable Voice (telephony)
- OpenAI Responses API (LLM + vision, optional but integrated)
- PostgreSQL + SQLAlchemy (persistent data)
- Docker Compose (local deployment)

## Quick Start
1. Copy environment file:
   ```bash
   cp .env.example .env
   ```
2. Start the stack:
   ```bash
   docker compose up --build
   ```
   This runs database migrations automatically (`alembic upgrade head`) before seeding.
3. Verify service:
   - API health: `http://localhost:8000/health`

## Database Migrations (Alembic)
- Apply latest migrations:
  ```bash
  alembic upgrade head
  ```
- Create a new migration after model changes:
  ```bash
  alembic revision --autogenerate -m "describe change"
  ```

## Twilio Setup
1. Create/choose a Twilio phone number.
2. Configure incoming voice webhook URL:
   - `POST https://<your-public-url>/voice/incoming`
3. For local testing, use ngrok:
   ```bash
   ngrok http 8000
   ```
   Then set Twilio webhook to `https://<ngrok-id>.ngrok-free.app/voice/incoming`.

## STT/TTS/LLM Strategy
- **STT**: Twilio speech capture via `Gather(input="speech")` optimized for phone-call acoustic models.
- **TTS**: Twilio TTS voice responses through TwiML `say`.
- **LLM Orchestration**: OpenAI Responses API for appliance extraction and image analysis; deterministic business actions remain server-side for reliability.

## Tier 3 Visual Diagnosis Flow
1. Agent asks for customer email when visual context is likely helpful.
2. Backend generates a unique upload token and emails a secure upload link.
3. Customer uploads image at `/media/upload/{token}`.
4. Vision analysis stores:
   - detected appliance type
   - visible issues summary
   - recommended next step
5. Voice flow uses that analysis in follow-up troubleshooting guidance.

## Call Flow
1. Greeting and appliance identification
2. Symptom collection:
   - what is happening
   - when it started
   - error code
   - unusual sounds
3. Guided troubleshooting steps
4. If unresolved:
   - collect ZIP code
   - collect preferred time window (morning/afternoon/evening/any)
   - offer first matching technician slot
5. Confirm booking and finalize appointment

## Database Tables
- `technicians`
- `technician_service_areas`
- `technician_specialties`
- `technician_availability`
- `appointments`
- `call_sessions`
- `image_uploads`

## Seed Data
The container startup runs:
```bash
python -m scripts.seed_data
```
It seeds representative technician/service-area/specialty/availability records once.

## Environment Variables
Use `.env.example` as reference. Important keys:
- `OPENAI_API_KEY`: enables LLM + vision analysis. If omitted, system falls back safely.
- `PUBLIC_BASE_URL`: used to generate upload links emailed to callers.
- `SMTP_*`: optional SMTP delivery; if unset, upload links are printed in logs for development.

## Notes and Extensions
- To productionize:
  - Add authentication for internal admin endpoints
  - Add retries/observability/logging
  - Add conflict-safe booking transaction isolation and idempotency keys
  - Upgrade from TwiML gather loops to Twilio Media Streams for low-latency streaming STT/TTS
