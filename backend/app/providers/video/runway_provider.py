from app.providers.video.base import VideoProvider

class RunwayProvider(VideoProvider):
    async def generate_video(self, prompt: str, duration: float, output_path: str, width: int = 1920, height: int = 1080) -> str:
        raise NotImplementedError("Runway Gen-2/Gen-3 commercial API provider is optional.")
