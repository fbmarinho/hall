import pytesseract
from docx import Document
from PIL import Image
import os

# Configure Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Update the path for your OS
os.environ['TESSDATA_PREFIX'] = r'C:\Program Files\Tesseract-OCR\tessdata'  # Update accordingly

# Load the DOCX file
doc = Document(r'C:\users\thale\desktop\temp\Test-compressed.docx')  # Replace with your file name

# Extract images from the DOCX
image_paths = []
for rel in doc.part.rels.values():
    if "image" in rel.target_ref:
        img_data = rel.target_part.blob
        img_path = r'C:\users\thale\desktop\temp\image'
        img_path += f"_{len(image_paths)+1}.jpg"
        with open(img_path, "wb") as f:
            f.write(img_data)
        image_paths.append(img_path)

# Perform OCR on the images
ocr_results = []
for img_path in image_paths:
    img = Image.open(img_path)
    text = pytesseract.image_to_string(img, lang='nor')  # Use Norwegian language for OCR
    ocr_results.append(text)

# Combine and save results
ocr_combined_text = "\n\n".join(ocr_results)
with open("output.txt", "w", encoding="utf-8") as f:
    f.write(ocr_combined_text)

print("OCR completed. Text saved to output.txt")