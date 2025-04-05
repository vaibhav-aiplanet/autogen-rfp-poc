import os
import tempfile
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker
from pydantic import SecretStr

from app.core.config import config


class PDFParser:
    def __init__(self):
        """
        Initialization of Semantic chunking splitter and HuggingFaceEmbeddings
        """

        self.embed_model = HuggingFaceInferenceAPIEmbeddings(
            api_key=SecretStr(config.HUGGINGFACE_API_KEY),
            model_name=config.HUGGINGFACE_MODEL_NAME,
            api_url=config.HUGGINGFACE_API_URL,
        )
        # self.semantic_chunker = SemanticChunker(
        #     self.embed_model, breakpoint_threshold_type="percentile"
        # )

        self.semantic_chunker = RecursiveCharacterTextSplitter(
            chunk_size=500, chunk_overlap=100
        )

    def extract_text_from_pdf(self, file_bytes: bytes):
        """
        Extracts text from a PDF file using PyPDFLoader.
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(file_bytes)
                tmp_path = tmp_file.name

            loader = PyPDFLoader(tmp_path)
            pages = loader.load()

            text = "\n".join(page.page_content for page in pages)

            os.unlink(tmp_path)

            if not text.strip():
                print("No text extracted from PDF.")
                raise ValueError("No text extracted from PDF.")

            print(f"Extracted text length: {len(text)} characters.")
            return text, pages
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            if "tmp_path" in locals():
                try:
                    os.unlink(tmp_path)
                except:
                    pass
            raise ValueError("Failed to extract text from PDF.")

    def create_documents_semantic(self, pages: list[Document]):
        """
        Performs semantic chunking to the text.
        """
        # result = self.semantic_chunker.create_documents([d.page_content for d in pages])
        chunked_docs: list[Document] = []
        for page in pages:
            chunks = self.semantic_chunker.create_documents([page.page_content])
            for chunk in chunks:
                chunk.metadata = page.metadata  # Retain original metadata
                chunked_docs.append(chunk)
        return chunked_docs


if __name__ == "__main__":
    file_processing = PDFParser()
    pdf_path = Path.cwd() / "sample_pdf.pdf"
    with open(pdf_path, "rb") as file:
        file_obj = file.read()
    text, pages = file_processing.extract_text_from_pdf(file_bytes=file_obj)
    semantic_chunks = file_processing.create_documents_semantic(pages=pages)
    for semantic_chunk in semantic_chunks:
        print(len(semantic_chunk.page_content))
