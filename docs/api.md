# REST API Documentation — AI Video Studio

FastAPI automatically generates interactive OpenAPI documentation at `http://localhost:8000/docs`.

## Key REST Endpoints

### Authentication
- `POST /api/auth/register`: Register new user account.
- `POST /api/auth/login`: Login & obtain JWT Bearer access token.
- `GET  /api/auth/me`: Fetch authenticated user profile.

### Projects & Styles
- `POST /api/projects`: Create new video channel/project with default style profile.
- `GET  /api/projects`: List all user projects.
- `GET  /api/projects/{id}`: Fetch project details.
- `PUT  /api/projects/{id}/style`: Update style profile (aspect ratio, resolution, colors, transition, music volume, logo).

### Assets
- `POST /api/projects/{id}/assets`: Upload media asset (IMAGE, VIDEO, AUDIO, MUSIC, VOICE, LOGO).
- `GET  /api/projects/{id}/assets`: List project assets filtered by type.
- `DELETE /api/assets/{id}`: Delete asset.

### Scripts & Scenes
- `POST /api/projects/{id}/scripts`: Save script content.
- `POST /api/scripts/{id}/analyze`: Analyze script using LLM/rule provider and generate structured scenes.
- `PUT  /api/scenes/{scene_id}`: Update scene narration, duration, visual asset, caption, or transition.

### Video Jobs & Rendering
- `POST /api/scripts/{id}/generate-video`: Enqueue background rendering job.
- `GET  /api/jobs/{id}`: Poll rendering job status & progress percentage.
- `GET  /api/videos`: List all rendered MP4 videos.
- `GET  /api/videos/{id}/stream`: Stream/download final MP4 video file.
