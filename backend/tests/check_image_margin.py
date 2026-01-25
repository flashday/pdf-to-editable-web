"""检查图片左边距"""
from PIL import Image

img_path = 'temp/7a9643ba-8ae4-4878-8d75-a2a53e3622e3_page1.png'
img = Image.open(img_path)
print(f'Image size: {img.size}')

pixels = img.load()

# 检查左边有多少列是纯白色
left_margin = 0
for x in range(min(200, img.size[0])):
    is_white_col = True
    for y in range(0, img.size[1], 20):
        r, g, b = pixels[x, y][:3]
        if r < 250 or g < 250 or b < 250:
            is_white_col = False
            break
    if is_white_col:
        left_margin = x + 1
    else:
        break

print(f'Left white margin: {left_margin} pixels')

# 检查第一个非白色像素的位置
for x in range(img.size[0]):
    for y in range(img.size[1]):
        r, g, b = pixels[x, y][:3]
        if r < 240 or g < 240 or b < 240:
            print(f'First non-white pixel at: ({x}, {y})')
            break
    else:
        continue
    break
