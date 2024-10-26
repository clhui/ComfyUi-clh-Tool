import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import torch
import numpy as np

import random
import folder_paths
# from nodes import PreviewImage

RESOURCES_DIR = os.path.join(Path(__file__).parent, "")


class FatLabels2:
    def __init__(self):
        self.device = "cpu"
        self.output_dir = folder_paths.get_temp_directory()
        self.type = "temp"
        self.prefix_append = "_temp_" + ''.join(random.choice("abcdefghijklmnopqrstupvxyz") for x in range(5))
        self.compress_level = 1

    @classmethod
    def INPUT_TYPES(cls):

        # input_dir = folder_paths.get_input_directory()
        # files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default1": "Hello", "forceInput": True}),
                "font_size": ("INT", {"default": 36, "min": 1}),  # Font size in pixels
            },
            "optional": {
                "font_path": ("STRING", {"image_upload": True}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "create_fat_label_with_cv2"
    CATEGORY = "simpleTool_clh"

    def create_fat_label_with_cv2(self, text, font_size, font_path, prompt=None, extra_pnginfo=None):
        # app.graph.title = text
        # Create a blank grayscale image as canvas with a fixed background color
        bg_color = 0  # Black background (grayscale)
        # text = text.encode("utf-8")

        # Create a drawing context to calculate text size
        text_width, text_height = self.calculate_text_size(text, font_size, font_path)

        # Calculate canvas dimensions with padding
        canvas_width = text_width + 40  # Add 20px padding on each side
        canvas_height = text_height + 40  # Add 20px padding on each side

        canvas = Image.new("L", (canvas_width, canvas_height), bg_color)

        # Font color is always white
        font_color = 255  # White (grayscale)

        # Create an ImageFont object with the desired font size
        font = self.get_font(font_size)

        # Create a drawing context
        draw = ImageDraw.Draw(canvas)

        # Calculate text position
        x = (canvas_width - text_width) // 2
        y = (canvas_height - text_height) // 2

        # Draw text on the image with the specified font size
        draw.text((x, y), text, fill=font_color, font=font)

        # Convert the image to a PyTorch tensor
        data = np.array(canvas)
        # tensor_data = torch.tensor(data, dtype=torch.float32)
        astype_data = data.astype(np.float32) / 255.0  # 先确保NumPy数组是float32
        tensor_data = torch.as_tensor(astype_data, dtype=torch.float32)
        image_tensor_out = tensor_data.unsqueeze(0)

        # image_tensor_out = torch.from_numpy(data.astype(np.float32) / 255.0).unsqueeze(0)
        results = list()
        return {
            "result": (image_tensor_out,),
            "ui": {
                "text": ['1234'],
                # "images": (data,),
            }
        }

    @staticmethod
    def get_font(font_size, font_path=None):
        if font_path is None or len(font_path) == 0:
            font_path = str(Path(os.path.join(RESOURCES_DIR, '../font/simhei.ttf')))
        elif font_path.startswith("./"):
            font_path = str(Path(os.path.join(RESOURCES_DIR, font_path)))
        return ImageFont.truetype(font_path, font_size)

    def calculate_text_size(self, text, font_size, font_path):
        # Create a temporary canvas to calculate text size
        canvas = Image.new("L", (1, 1), 0)  # Create a blank 1x1 grayscale image
        draw = ImageDraw.Draw(canvas)
        font = self.get_font(font_size, font_path)
        left, top, right, bottom = draw.textbbox((0, 0), text, font)
        text_width, text_height = right, bottom
        return text_width, text_height


NODE_CLASS_MAPPINGS = {
    "FatLabels_clh": FatLabels2,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FatLabels_clh": "FatLabels_clh",

}
