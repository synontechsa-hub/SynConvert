from PIL import Image
import os

png_path = r'd:\Coding\SynonTech\SynConvert\SynConvert_v1.0.6\frontend\assets\logo.png'
ico_path = r'd:\Coding\SynonTech\SynConvert\SynConvert_v1.0.6\frontend\windows\runner\resources\app_icon.ico'

try:
    img = Image.open(png_path)
    # Windows icons usually contain multiple sizes: 16, 32, 48, 64, 128, 256
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format='ICO', sizes=icon_sizes)
    print(f"Successfully converted {png_path} to {ico_path}")
except Exception as e:
    print(f"Error converting icon: {e}")
