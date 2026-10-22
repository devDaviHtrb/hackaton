import io
from pypdf import PdfReader

def extract_file_text(byte_content: bytes, filename: str ) -> str:
    # If the file input is .txt
    if filename.endswith(".txt"):
        return byte_content.decode("utf-8")

    elif filename.endswith(".pdf"):
        # transform the bytes sequence into a file in memory
        # PdfReader cannot read raw bytes
        stream = io.BytesIO(byte_content)

        # Pass the stream(File In Memory) to PdfReader obj
        reader = PdfReader(stream)

        text = []

        for page in reader.pages:
            # Extract current page txt
            text_page = page.extract_text()

            if text_page:
                text.append(text_page)

        # return the str divided by pages (\n)
        return "\n".join(text)
