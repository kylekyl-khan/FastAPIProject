from PIL import Image, ImageDraw

# Create a simple 64x64 icon
icon_size = (64, 64)
icon = Image.new('RGB', icon_size, color=(0, 120, 215))  # Office blue color
draw = ImageDraw.Draw(icon)

# Draw a simple envelope shape to represent email
draw.rectangle([10, 20, 54, 44], outline='white', width=2)  # Mailbox
draw.polygon([(10, 20), (32, 35), (54, 20)], fill='white')  # Envelope flap

# Save as PNG
icon.save('static/icon.png')
print("Icon created successfully: static/icon.png")