# ExtractTextService.py
#
# Extração do texto cru de um arquivo enviado pelo usuário (PDF ou TXT).
# É o primeiro passo do pipeline: o texto retornado aqui é o que alimenta
# o Gemini (analyze_article) e, mais tarde, o cálculo de importância.

import io
from pypdf import PdfReader

def extract_file_text(byte_content: bytes, filename: str ) -> str:
    # Recebe os bytes do upload (request.files...read()) e o nome do arquivo,
    # que é usado apenas para decidir o formato pela extensão.

    # TXT: decodifica direto como UTF-8 (assume codificação padrão do arquivo).
    if filename.endswith(".txt"):
        return byte_content.decode("utf-8")

    elif filename.endswith(".pdf"):
        # O PdfReader não lê bytes crus; embrulhamos num stream em memória
        # (BytesIO) para evitar gravar um arquivo temporário em disco.
        stream = io.BytesIO(byte_content)

        # Pass the stream(File In Memory) to PdfReader obj
        reader = PdfReader(stream)

        text = []

        # Extrai o texto página a página; páginas sem texto (ex.: imagens
        # escaneadas sem OCR) retornam vazio e são ignoradas.
        for page in reader.pages:
            text_page = page.extract_text()

            if text_page:
                text.append(text_page)

        # Junta as páginas com quebra de linha. Observação: a informação de
        # "qual página" não é preservada aqui — por isso o campo "using" do
        # Gemini (page/line) acaba vindo sem posições reais.
        return "\n".join(text)