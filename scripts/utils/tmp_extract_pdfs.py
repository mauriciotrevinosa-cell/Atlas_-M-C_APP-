import os
import PyPDF2

folder = r"c:\Users\mauri\OneDrive\Desktop\Atlas\info_instructions"
output_file = r"c:\Users\mauri\OneDrive\Desktop\Atlas\tmp_pdf_extract.txt"

pdfs = [
    "edu-2014-exam-quant-fin-invest-formula.pdf",
    "formula_sheet_for_financial_mathematics.pdf",
    "quantum_finance_ictp_day1_part1_and_part2-.pdf",
    "qb.pdf",
    "qm.pdf"
]

with open(output_file, 'w', encoding='utf-8') as out:
    for pdf_name in pdfs:
        pdf_path = os.path.join(folder, pdf_name)
        if not os.path.exists(pdf_path):
            continue
            
        out.write(f"\n{'='*50}\n--- {pdf_name} ---\n{'='*50}\n")
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                num_pages = len(reader.pages)
                # Max 20 pages per pdf to avoid endless text
                pages_to_read = min(num_pages, 20)
                for i in range(pages_to_read):
                    page = reader.pages[i]
                    text = page.extract_text()
                    if text:
                        out.write(f"\n[Page {i+1}]\n")
                        out.write(text)
        except Exception as e:
            out.write(f"\nError reading {pdf_name}: {e}\n")

print(f"Extraction saved to {output_file}")
