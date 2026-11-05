#!/usr/bin/env python3
"""Create TraceLens presentation PPTX."""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

def add_title_slide(prs, title, subtitle):
    """Add title slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = title
    slide.placeholders[1].text = subtitle
    return slide

def add_content_slide(prs, title, content_items):
    """Add content slide with bullet points."""
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = title
    
    text_frame = slide.placeholders[1].text_frame
    text_frame.clear()
    
    for item in content_items:
        p = text_frame.add_paragraph()
        p.text = item
        p.level = 0
        p.space_before = Pt(6)
    
    return slide

def add_two_column_slide(prs, title, left_items, right_items):
    """Add two-column slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = title
    
    # Left column
    left_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(4.5), Inches(5))
    tf_left = left_box.text_frame
    tf_left.word_wrap = True
    
    for item in left_items:
        p = tf_left.add_paragraph()
        p.text = item
        p.space_before = Pt(6)
    
    # Right column
    right_box = slide.shapes.add_textbox(Inches(5.2), Inches(1.5), Inches(4.5), Inches(5))
    tf_right = right_box.text_frame
    tf_right.word_wrap = True
    
    for item in right_items:
        p = tf_right.add_paragraph()
        p.text = item
        p.space_before = Pt(6)
    
    return slide

def main():
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)
    
    # Slide 1: Title
    add_title_slide(
        prs,
        "TraceLens",
        "JPEG Analyzer untuk Fingerprint Camera\n\nAnalisis Forensik Digital untuk Identifikasi Kamera"
    )
    
    # Slide 2: Latar Belakang - Kebutuhan
    add_content_slide(
        prs,
        "Latar Belakang: Kebutuhan Analisis Forensik",
        [
            "Analisis forensik digital untuk identifikasi kamera sumber foto",
            "Setiap kamera memiliki karakteristik unik dalam kompresi JPEG",
            "Quantization tables sebagai fingerprint kamera",
            "Berbeda dengan analisis PRNU (Pattern Response Noise Unit)",
            "Use case: verifikasi keaslian foto, identifikasi sumber kamera"
        ]
    )
    
    # Slide 3: Latar Belakang - Quantization Tables
    add_content_slide(
        prs,
        "JPEG Quantization Tables sebagai Fingerprint",
        [
            "Setiap kamera menggunakan quantization tables spesifik",
            "Tabel 8x8 untuk Luma (Y) dan Chroma (Cb, Cr)",
            "64 nilai per tabel mencerminkan karakteristik encoder",
            "Pola unik per manufacturer dan model kamera",
            "Dapat diekstrak dari file JPEG tanpa modifikasi"
        ]
    )
    
    # Slide 4: Metodologi - Arsitektur
    add_two_column_slide(
        prs,
        "Metodologi: Arsitektur Aplikasi",
        [
            "Frontend:",
            "• Vue 3 + Composition API",
            "• Tailwind CSS untuk styling",
            "• Responsive design (390px - 1200px)",
            "",
            "Backend:",
            "• FastAPI (Python 3.11+)",
            "• Async/await untuk performa",
            "• RESTful API endpoints"
        ],
        [
            "Database:",
            "• SQLite untuk storage",
            "• 102 kamera referensi",
            "• Quantization tables + metadata",
            "",
            "Development:",
            "• Agile methodology",
            "• Tim 6 agent AI",
            "• 10 test cases QA"
        ]
    )
    
    # Slide 5: Metodologi - Data Collection
    add_content_slide(
        prs,
        "Data Collection: 102 Kamera Referensi",
        [
            "Sumber: ExifTool Meta Information Repository",
            "Authentic JPEG dengan EXIF metadata lengkap",
            "Berbagai manufacturer: Canon, Nikon, Sony, dll",
            "Extract quantization tables menggunakan libjpeg",
            "Validasi: Make/Model matching dengan EXIF data"
        ]
    )
    
    # Slide 6: Metodologi - Development Team
    add_content_slide(
        prs,
        "Development Approach: Agile dengan AI Agents",
        [
            "Stack PM: Koordinasi tim dan arsitektur",
            "Vue-FastAPI Builder: Implementasi frontend & backend",
            "Bug Fixer: Debugging dan fixing issues",
            "QA Tester: Testing dan quality assurance",
            "Product Design Lead: UI/UX design",
            "Project Partner: Planning dan dokumentasi"
        ]
    )
    
    # Slide 7: Metodologi Deteksi - Extract
    add_content_slide(
        prs,
        "Metodologi Deteksi: Extract Quantization Tables",
        [
            "Upload file JPEG dari user",
            "Extract 2 quantization tables:",
            "  • Table 0: Luma (Y) - 8x8 = 64 values",
            "  • Table 1: Chroma (Cb, Cr) - 8x8 = 64 values",
            "Normalisasi nilai untuk comparison",
            "Simpan sebagai array 1D untuk processing"
        ]
    )
    
    # Slide 8: Metodologi Deteksi - Comparison
    add_content_slide(
        prs,
        "Metodologi Deteksi: Comparison & Scoring",
        [
            "Compare uploaded JPEG vs 102 referensi",
            "Similarity scoring:",
            "  • Table similarity (cosine similarity)",
            "  • EXIF Make/Model matching",
            "",
            "Boost logic:",
            "  • +15% untuk exact model match",
            "  • +5% untuk same brand match"
        ]
    )
    
    # Slide 9: Metodologi Deteksi - Confidence Levels
    add_content_slide(
        prs,
        "Confidence Levels",
        [
            "≥ 0.75: KUAT - Identifikasi sangat meyakinkan",
            "≥ 0.55: SEDANG - Identifikasi cukup meyakinkan",
            "≥ 0.45: LEMAH - Indikasi awal, perlu verifikasi",
            "< 0.45: TIDAK DAPAT DIPASTIKAN",
            "",
            "Output: Top 3 kandidat kamera dengan similarity %"
        ]
    )
    
    # Slide 10: Halaman Upload
    add_content_slide(
        prs,
        "Halaman Upload (/)",
        [
            "Drag & drop area untuk upload JPEG",
            "Preview image sebelum analisis",
            "Tombol 'Analisis' untuk memulai proses",
            "Validasi file type (JPEG only)",
            "Loading state saat processing",
            "Redirect ke halaman hasil setelah selesai"
        ]
    )
    
    # Slide 11: Halaman Referensi
    add_content_slide(
        prs,
        "Halaman Referensi (/referensi)",
        [
            "Daftar 102 kamera dengan search filter",
            "Heatmap visualization quantization tables",
            "Expand untuk lihat detail:",
            "  • Luma 8x8 matrix",
            "  • Chroma 8x8 matrix",
            "  • Min/Max statistics",
            "Responsive: mobile (390px) + desktop (1200px)"
        ]
    )
    
    # Slide 12: Halaman Hasil
    add_content_slide(
        prs,
        "Halaman Hasil (/hasil/[id])",
        [
            "Verdict: KUAT / SEDANG / LEMAH",
            "Confidence score (0-100%)",
            "Top 3 kandidat kamera:",
            "  • Camera name",
            "  • Similarity percentage",
            "  • EXIF metadata",
            "Encoder info: libjpeg IJG, Adobe-style, dll"
        ]
    )
    
    # Slide 13: Halaman Laporan
    add_content_slide(
        prs,
        "Halaman Laporan (/laporan/[id])",
        [
            "Printable report untuk dokumentasi forensik",
            "Format profesional untuk arsip",
            "Berisi:",
            "  • Informasi file yang dianalisis",
            "  • Hasil identifikasi kamera",
            "  • Quantization tables visualization",
            "  • Timestamp analisis",
            "Export: Print to PDF"
        ]
    )
    
    # Slide 14: Halaman Pengaturan
    add_content_slide(
        prs,
        "Halaman Pengaturan (/pengaturan)",
        [
            "Konfigurasi aplikasi TraceLens",
            "Pengaturan database referensi",
            "Threshold confidence levels",
            "Informasi versi aplikasi",
            "About: tim pengembang dan lisensi"
        ]
    )
    
    # Slide 15: Yang Dihasilkan
    add_content_slide(
        prs,
        "Output Analisis TraceLens",
        [
            "✓ Identifikasi kamera dengan confidence level",
            "✓ Top 3 kandidat kamera paling mirip",
            "✓ Quantization table visualization (heatmap)",
            "✓ EXIF metadata extraction",
            "✓ Encoder fingerprint detection",
            "✓ Printable forensic report"
        ]
    )
    
    # Slide 16: Evaluasi - Dataset
    add_content_slide(
        prs,
        "Evaluasi Pengembangan: Dataset",
        [
            "Target: 200+ kamera referensi",
            "Integrasi database forensik publik:",
            "  • Dresden Image Database",
            "  • RAISE (Realistic Adversarial Images)",
            "Diversifikasi manufacturer dan model",
            "Update berkala dengan kamera baru"
        ]
    )
    
    # Slide 17: Evaluasi - Fitur
    add_content_slide(
        prs,
        "Evaluasi Pengembangan: Fitur Tambahan",
        [
            "Analisis edit trace detection:",
            "  • Thumbnail vs main table mismatch",
            "  • Deteksi editing software",
            "",
            "Export format standar forensik:",
            "  • CSV, JSON, PDF",
            "",
            "API untuk integrasi sistem lain",
            "Multi-language support (currently Indonesian)"
        ]
    )
    
    # Slide 18: Penutup
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Penutup"
    
    text_frame = slide.placeholders[1].text_frame
    text_frame.clear()
    
    items = [
        "TraceLens sebagai tools bantu analisis forensik digital",
        "Open source untuk komunitas forensik",
        "Feedback dan kontribusi welcome",
        "",
        "Terima kasih"
    ]
    
    for item in items:
        p = text_frame.add_paragraph()
        p.text = item
        p.space_before = Pt(6)
    
    return prs

if __name__ == "__main__":
    prs = main()
    output_path = "/Users/mashandri/OpenBot/Shared/PRNU-TraceLens/tracelens_presentation.pptx"
    prs.save(output_path)
    print(f"Presentation saved to: {output_path}")
    print(f"Total slides: {len(prs.slides)}")
