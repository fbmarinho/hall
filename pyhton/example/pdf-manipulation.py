import fitz  # PyMuPDF


DPI = 300  # render resolution for cropped images


def compute_crop_rect(page_rect, x0_rel, y0_rel, w_rel, h_rel):
    """
    Compute an absolute crop rectangle from relative (0..1) parameters.

    x0_rel, y0_rel: top-left corner as fraction of page width/height
    w_rel, h_rel:   width/height as fraction of page width/height
    """
    W = page_rect.width
    H = page_rect.height

    # Optional safety clamp
    x0_rel = max(0.0, min(1.0, x0_rel))
    y0_rel = max(0.0, min(1.0, y0_rel))
    w_rel = max(0.0, min(1.0, w_rel))
    h_rel = max(0.0, min(1.0, h_rel))

    x0 = W * x0_rel
    y0 = H * y0_rel
    x1 = x0 + W * w_rel
    y1 = y0 + H * h_rel

    # Ensure we don't go outside the page
    x1 = min(x1, W)
    y1 = min(y1, H)

    return fitz.Rect(x0, y0, x1, y1)


def merge_cropped_regions_parametric(
    pdf1_path,
    pdf2_path,
    output_path,
    # These are your tunable parameters (0..1)
    crop1_params=(0.0, 0.0, 0.4, 0.2),   # x0, y0, w, h for first PDF
    crop2_params=(0.0, 0.4, 0.4, 0.2),   # x0, y0, w, h for second PDF
):
    # Open both documents
    doc1 = fitz.open(pdf1_path)
    doc2 = fitz.open(pdf2_path)

    page1 = doc1[0]
    page2 = doc2[0]

    rect1 = page1.rect
    rect2 = page2.rect

    # Unpack parameters
    x0_1, y0_1, w_1, h_1 = crop1_params
    x0_2, y0_2, w_2, h_2 = crop2_params

    # Compute crop rects based on your relative parameters
    crop1 = compute_crop_rect(rect1, x0_1, y0_1, w_1, h_1)
    crop2 = compute_crop_rect(rect2, x0_2, y0_2, w_2, h_2)

    # Render cropped regions to pixmaps (images)
    pix1 = page1.get_pixmap(clip=crop1, dpi=DPI)
    pix2 = page2.get_pixmap(clip=crop2, dpi=DPI)

    img1_bytes = pix1.tobytes("png")
    img2_bytes = pix2.tobytes("png")

    # Create output document with a single A4 page
    out_doc = fitz.open()
    a4 = fitz.paper_rect("a4")
    out_page = out_doc.new_page(width=a4.width, height=a4.height)

    # Here we just place the cropped images at the *same* coordinates
    # as their crop rectangles, assuming the page size is also A4.
    # (If your originals are A4, this matches positions nicely.)

    def clamp_rect_to_a4(r, a4_rect):
        x0 = max(a4_rect.x0, r.x0)
        y0 = max(a4_rect.y0, r.y0)
        x1 = min(a4_rect.x1, r.x1)
        y1 = min(a4_rect.y1, r.y1)
        return fitz.Rect(x0, y0, x1, y1)

    target1 = clamp_rect_to_a4(crop1, a4)
    target2 = clamp_rect_to_a4(crop2, a4)

    out_page.insert_image(target1, stream=img1_bytes)
    out_page.insert_image(target2, stream=img2_bytes)

    out_doc.save(output_path)
    out_doc.close()
    doc1.close()
    doc2.close()

if __name__ == "__main__":
    # Start with a guess, then tweak the 4 numbers for each crop until it looks right
    merge_cropped_regions_parametric(
        pdf1_path=r"C:\Users\thale\desktop\Image-Front.pdf",
        pdf2_path=r"C:\Users\thale\desktop\Image-Back.pdf",
        output_path=r"C:\Users\thale\desktop\Image-Merged.pdf",
        crop1_params=(0.0, 0.0, 0.6, 0.4),  # first PDF: top-left-ish, 40% width, 20% height
        crop2_params=(0.0, 0.45, 0.6, 0.4),  # second PDF: middle-left-ish
    )
