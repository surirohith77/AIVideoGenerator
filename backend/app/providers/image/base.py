from abc import ABC, abstractmethod

class ImageProvider(ABC):
    @abstractmethod
    async def generate_image(self, prompt: str, output_path: str, width: int = 1920, height: int = 1080) -> str:
        pass
