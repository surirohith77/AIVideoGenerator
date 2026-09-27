from abc import ABC, abstractmethod

class VideoProvider(ABC):
    @abstractmethod
    async def generate_video(self, prompt: str, duration: float, output_path: str, width: int = 1920, height: int = 1080) -> str:
        pass
