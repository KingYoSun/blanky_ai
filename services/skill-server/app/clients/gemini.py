from io import BytesIO
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types
from PIL import Image as PILImage

from app.config import Settings
from app.domain.artifacts import ArtifactStore


class NanoBananaService:
    model_name = "gemini-3-pro-image-preview"

    def __init__(self, settings: Settings, artifacts: ArtifactStore):
        self._settings = settings
        self._artifacts = artifacts

    def is_configured(self) -> bool:
        return bool(self._settings.gemini_api_key)

    def generate(
        self,
        prompt: str,
        resolution: str,
        filename_hint: str | None,
        input_files: list[dict[str, Any]],
        request_id: str,
    ) -> dict[str, Any]:
        if not self._settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured in skill-server.")

        input_images, resolved_resolution = self._load_images(input_files, resolution)
        contents: str | list[Any] = prompt
        if input_images:
            contents = [*input_images, prompt]

        client = genai.Client(api_key=self._settings.gemini_api_key)
        artifact_path, client_visible_path = self._artifacts.build_paths(filename_hint)

        image_saved = False
        image_width = None
        image_height = None
        text_responses: list[str] = []

        for chunk in client.models.generate_content_stream(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(image_size=resolved_resolution),
            ),
        ):
            if chunk.parts is None:
                continue

            for part in chunk.parts:
                if part.text is not None:
                    text_responses.append(part.text)
                    continue

                if part.inline_data is None or not part.inline_data.data:
                    continue

                image_data = part.inline_data.data
                if isinstance(image_data, str):
                    import base64

                    image_data = base64.b64decode(image_data)

                image = PILImage.open(BytesIO(image_data))
                saved_image = self._save_png(image, artifact_path)
                image_width, image_height = saved_image.size
                image_saved = True

        if not image_saved:
            raise RuntimeError("No image was generated in the response.")

        return {
            "artifact_path": str(artifact_path),
            "media_path": str(client_visible_path),
            "width": image_width,
            "height": image_height,
            "model": self.model_name,
            "request_id": request_id,
            "text_responses": text_responses,
        }

    def _load_images(
        self, input_files: list[dict[str, Any]], resolution: str
    ) -> tuple[list[PILImage.Image], str]:
        if len(input_files) > self._settings.max_input_images:
            raise RuntimeError(
                f"Too many input images ({len(input_files)}). "
                f"Maximum is {self._settings.max_input_images}."
            )

        images: list[PILImage.Image] = []
        max_input_dim = 0
        resolved_resolution = resolution

        for file_info in input_files:
            image = PILImage.open(BytesIO(file_info["data"]))
            copied = image.copy()
            images.append(copied)
            max_input_dim = max(max_input_dim, *copied.size)

        if images and resolution == "1K":
            if max_input_dim >= 3000:
                resolved_resolution = "4K"
            elif max_input_dim >= 1500:
                resolved_resolution = "2K"

        return images, resolved_resolution

    def _save_png(self, image: PILImage.Image, output_path: Path) -> PILImage.Image:
        if image.mode == "RGBA":
            rgb_image = PILImage.new("RGB", image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])
            rgb_image.save(str(output_path), "PNG")
            return rgb_image

        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(str(output_path), "PNG")
        return image
