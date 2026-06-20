from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A6
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm
import os

def create_receipt():
    # Create PDF
    c = canvas.Canvas("receipt.pdf", pagesize=A6)
    width, height = A6
    
    # Starting Y position from top
    y = height - 20
    
    # ============================================
    # HEADER WITH LOGO (Left, Center, Right)
    # ============================================
    
    # Left Logo
    if os.path.exists("logo.png"):
        img = ImageReader("logo.png")
        c.drawImage(img, 30, y-30, width=40, height=40, preserveAspectRatio=True)
    
    # Center Title
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, y-10, "AUTO CARE")
    c.setFont("Helvetica", 8)
    c.drawCentredString(width/2, y-25, "123 Main Street, Harare")
    c.drawCentredString(width/2, y-35, "Tel: +263 712 345 678")
    
    # Right Logo
    if os.path.exists("logo.png"):
        img = ImageReader("logo.png")
        c.drawImage(img, width-70, y-30, width=40, height=40, preserveAspectRatio=True)
    
    # Update Y position
    y = y - 55
    
    # ============================================
    # DIVIDER
    # ============================================
    c.line(30, y, width-30, y)
    y -= 10
    
    # ============================================
    # INVOICE DETAILS (Left and Right)
    # ============================================
    c.setFont("Helvetica", 8)
    c.drawString(30, y, "Invoice #: INV-2026-001")
    c.drawRightString(width-30, y, "Date: 2026-06-18")
    y -= 10
    
    c.drawString(30, y, "Cashier: Admin")
    c.drawRightString(width-30, y, "Time: 15:30:00")
    y -= 10
    
    # ============================================
    # DIVIDER
    # ============================================
    c.line(30, y, width-30, y)
    y -= 10
    
    # ============================================
    # TABLE HEADER (Left, Center, Right)
    # ============================================
    c.setFont("Helvetica-Bold", 8)
    c.drawString(30, y, "ITEM")
    c.drawCentredString(width/2, y, "QTY")
    c.drawRightString(width-30, y, "TOTAL")
    y -= 8
    
    c.setFont("Helvetica", 7)
    c.line(30, y, width-30, y)
    y -= 5
    
    # ============================================
    # TABLE ROWS
    # ============================================
    items = [
        ("Brake Pads", "2", "$120.00"),
        ("Engine Oil", "1", "$45.00"),
        ("Spark Plugs", "4", "$80.00"),
        ("Air Filter", "1", "$25.00"),
    ]
    
    for item, qty, price in items:
        c.drawString(30, y, item)
        c.drawCentredString(width/2, y, qty)
        c.drawRightString(width-30, y, price)
        y -= 10
    
    # ============================================
    # DIVIDER
    # ============================================
    y -= 5
    c.line(30, y, width-30, y)
    y -= 10
    
    # ============================================
    # TOTALS (Right Aligned)
    # ============================================
    c.setFont("Helvetica", 8)
    c.drawRightString(width-30, y, "Subtotal: $270.00")
    y -= 10
    c.drawRightString(width-30, y, "Discount: -$20.00")
    y -= 10
    c.drawRightString(width-30, y, "VAT: $32.40")
    y -= 10
    
    c.line(30, y, width-30, y)
    y -= 10
    
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width-30, y, "TOTAL: $282.40")
    y -= 15
    
    # ============================================
    # PAYMENT (Left and Right)
    # ============================================
    c.setFont("Helvetica", 8)
    c.drawString(30, y, "Payment: CASH")
    c.drawRightString(width-30, y, "Paid: $300.00")
    y -= 10
    c.drawRightString(width-30, y, "Change: $17.60")
    y -= 15
    
    # ============================================
    # CENTERED FOOTER
    # ============================================
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width/2, y, "YOUR CAR KNOWS THE BEST")
    y -= 12
    
    c.setFont("Helvetica", 6)
    c.drawCentredString(width/2, y, "Thank you for your business!")
    y -= 8
    c.drawCentredString(width/2, y, "Visit us again!")
    y -= 8
    
    # ============================================
    # QR CODE (Center)
    # ============================================
    # If you have qrcode installed
    try:
        import qrcode
        from PIL import Image
        import io
        
        qr = qrcode.QRCode(version=1, box_size=4, border=1)
        qr.add_data("https://example.com/invoice/INV-2026-001")
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to temp
        temp_qr = "temp_qr.png"
        qr_img.save(temp_qr)
        
        if os.path.exists(temp_qr):
            img = ImageReader(temp_qr)
            qr_size = 40
            c.drawImage(img, width/2 - qr_size/2, y-50, width=qr_size, height=qr_size)
            os.remove(temp_qr)
    except:
        pass
    
    # ============================================
    # SAVE
    # ============================================
    c.save()
    print("✅ PDF created: receipt.pdf")

# Run it
create_receipt()