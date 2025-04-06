import io
import os
import tempfile
from typing import Any, Dict, List

import pandas as pd
import pdfplumber
import tiktoken
from langchain.docstore.document import Document
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from llama_index.core import SimpleDirectoryReader
from llama_parse import LlamaParse, ResultType

from app.core.config import config


class FileProcessing:
    def __init__(self):
        """
        Initializes the text splitter.
        """
        try:
            # Initialize Text Splitter
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=config.CHUNK_SIZE,
                chunk_overlap=config.CHUNK_OVERLAP,
                length_function=len,
            )
        except Exception as e:
            print(f"Error initializing TextSplitter: {str(e)}")
            raise

    async def extract_text_from_file(self, file_bytes: bytes, extension: str):
        """
        Asynchronously extracts text from a PDF file using LlamaParse.
        """
        tmp_path = None
        try:
            if extension.lower() == "xlsx":
                df = pd.read_excel(io.BytesIO(file_bytes))
                text = df.to_string(index=False)
                return text

            elif extension.lower() == "csv":
                df = pd.read_csv(io.BytesIO(file_bytes))
                text = df.to_string(index=False)
                return text

            elif extension.lower() == "txt":
                text = file_bytes.decode("utf-8")
                return text

            elif extension.lower() == "pdf":
                # Write file bytes to a temporary PDF file
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".pdf"
                ) as tmp_file:
                    tmp_file.write(file_bytes)
                    tmp_path = tmp_file.name

                # Initialize the parser (ensure you are using your own API key)
                parser = LlamaParse(
                    api_key=config.LLAMA_CLOUD_API_KEY,
                    result_type=ResultType.TXT,
                )
                file_extractor = {".pdf": parser}

                # Use the asynchronous loader
                reader = SimpleDirectoryReader(
                    input_files=[tmp_path],
                    file_extractor=file_extractor,  # type:ignore
                )
                documents = await reader.aload_data()  # Await the async method

                # Remove the temporary file
                os.unlink(tmp_path)

                if not documents:
                    print("No text extracted from PDF.")
                    raise ValueError("No text extracted from PDF.")

                # Join text from all documents
                text = "\n".join(doc.text for doc in documents)

                print(f"Extracted text from PDF: {text}")
                return text

        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            raise ValueError("Failed to extract text from PDF.")

    def split_text_into_chunks(self, text: str) -> List[str]:
        """
        Splits the extracted text into smaller chunks for embedding.
        """
        try:
            chunks = self.text_splitter.split_text(text)
            print(f"Text split into {len(chunks)} chunks.")
            return chunks
        except Exception as e:
            print(f"Error splitting text into chunks: {str(e)}")
            raise

    def create_documents(
        self, chunks: List[str], metadata: Dict[str, Any]
    ) -> List[Document]:
        """
        Creates Document objects from text chunks with associated metadata.
        """
        try:
            documents = [
                Document(page_content=chunk, metadata=metadata.copy())
                for chunk in chunks
            ]
            print(f"Created {len(documents)} Document objects.")
            return documents
        except Exception as e:
            print(f"Error creating Document objects: {str(e)}")
            raise

    def split_into_chunks_according_tokens(
        self, text_list: List[str], max_tokens=100000
    ):
        encoder = tiktoken.get_encoding("cl100k_base")

        def count_tokens(text):
            return len(encoder.encode(text))

        current_chunk = []
        current_token_count = 0
        chunks = []
        for text in text_list:
            tokens_in_text = count_tokens(text)

            if current_token_count + tokens_in_text > max_tokens:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [text]
                current_token_count = tokens_in_text
            else:
                current_chunk.append(text)
                current_token_count += tokens_in_text

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    def bytesToText(self, file_bytes: bytes) -> str:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text_content = ""
            for page in pdf.pages:
                text_content += page.extract_text()
        return text_content

    def split_text_recursively(self, text: str):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800, chunk_overlap=200
        )
        chunks = text_splitter.split_text(text)
        return chunks

    def read_file(self, file_path: str):
        with open(file_path, "rb") as f:
            content = f.read()
            return content
