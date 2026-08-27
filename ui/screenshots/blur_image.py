# Blurs input image book content

from PIL import Image, ImageFilter

# Input/output files
INPUT_FILE = "opened_book.png"
OUTPUT_FILE = "opened_book_blurred.png"

# Open image
img = Image.open(INPUT_FILE)

# Body text area only
# (x1, y1, x2, y2)
TEXT_REGION = (
    290, 220,   # top-left
    960, 780    # bottom-right
)

# Extract region
region = img.crop(TEXT_REGION)

# Apply blur
blurred = region.filter(
    ImageFilter.GaussianBlur(radius=4)
)

# Paste back
img.paste(blurred, TEXT_REGION)

# Save
img.save(OUTPUT_FILE)

print(f"Saved: {OUTPUT_FILE}")