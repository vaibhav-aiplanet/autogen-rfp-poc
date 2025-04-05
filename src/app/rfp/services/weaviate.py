import logging
import time
from typing import Any, Dict, Optional
from uuid import UUID

import aioboto3
import weaviate
from openai import AsyncAzureOpenAI
from weaviate.auth import Auth
from weaviate.collections.classes.filters import Filter
from weaviate.collections.classes.grpc import MetadataQuery, QueryReference

from app.core.config import config


def sanitize_class_name(folder_id: str) -> str:
    try:
        transformed = "Id_" + folder_id.replace("-", "_")
        return transformed
    except Exception as e:
        raise Exception(f"Error sanitizing class name: {str(e)}")


class WeaviateService:
    def __init__(self):
        """
        Initializes the Weaviate client and sets up embeddings and text splitter.
        """
        try:

            # self.client = weaviate.WeaviateClient(
            #     url=config.WEAVIATE_URL,
            #     auth_client_secret=weaviate.AuthApiKey(config.WEAVIATE_API_KEY),
            # )

            self.client = weaviate.connect_to_weaviate_cloud(
                config.WEAVIATE_URL,
                Auth.api_key(config.WEAVIATE_API_KEY),
                {"X-OpenAI-Api-key": config.OPENAI_API_KEY},
            )

            self.embeddings = AsyncAzureOpenAI(
                azure_deployment=config.AZURE_OPENAI_DEPLOYMENT,
                azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                api_key=config.AZURE_OPENAI_EMBEDDINGS_API_KEY,
                api_version=config.AZURE_OPENAI_API_VERSION,
            )
            logging.info("Embeddings initialized successfully.")

            self.model_id = config.COHERE_MODEL_ID
            self.model_package_arn = f"arn:aws:bedrock:{config.BEDROCK_REGION}::foundation-model/{self.model_id}"
        except Exception as e:
            logging.error(f"Error initializing WeaviateService: {str(e)}")
            raise

    async def generate_embedding(self, text):
        start_time = time.time()

        embedding = await self.embeddings.embeddings.create(
            model="text-embedding-3-small", input=[text]  # or your deployed model name
        )
        end_time = time.time()
        print(f"Embedding Generation Time: {end_time - start_time:.2f} seconds")

        return embedding.data[0].embedding

    async def rerank_text(self, text_query, text_sources, num_results):
        """Calls AWS Bedrock to rerank text asynchronously."""
        session = aioboto3.Session()
        async with session.client(
            "bedrock-agent-runtime",
            aws_access_key_id=config.BEDROCK_ACCESS_KEY,
            aws_secret_access_key=config.BEDROCK_SECRET_KEY,
            region_name=config.BEDROCK_REGION,
        ) as client:
            response = await client.rerank(
                queries=[{"type": "TEXT", "textQuery": {"text": text_query}}],
                sources=text_sources,
                rerankingConfiguration={
                    "type": "BEDROCK_RERANKING_MODEL",
                    "bedrockRerankingConfiguration": {
                        "numberOfResults": num_results,
                        "modelConfiguration": {"modelArn": self.model_package_arn},
                    },
                },
            )
        return response["results"]

    async def rerank(self, query: str, docs, top_n: int = config.TOP_K):
        """Formats documents for reranking and returns top-ranked results."""
        print(f"Reranking {len(docs)} documents...")
        print(f"Top-{top_n} results will be returned.")
        text_sources = []
        for doc in docs:
            text_sources.append(
                {
                    "type": "INLINE",
                    "inlineDocumentSource": {
                        "type": "TEXT",
                        "textDocument": {
                            "text": doc["text"],
                        },
                    },
                }
            )
        if len(text_sources) >= top_n:
            results = await self.rerank_text(query, text_sources, top_n)
        else:
            results = await self.rerank_text(query, text_sources, len(text_sources))

        ranked_docs = []
        for result in results:
            index = result["index"]
            score = result["relevanceScore"]
            # if score > 0.15:
            ranked_docs.append(
                {
                    "text": docs[index]["text"],
                    "filename": docs[index]["filename"],
                    "metadata": docs[index]["metadata"],
                    "rank_score": score,
                }
            )
        ranked_docs = sorted(ranked_docs, key=lambda x: x["rank_score"], reverse=True)
        return ranked_docs

    async def query_collection(
        self,
        folder_id: UUID,
        query: str,
        k: int = 25,
        filters: Optional[Dict[str, Any]] = None,
    ) -> list[dict]:
        """
        Queries a Weaviate class and retrieves the top-k relevant documents.
        Optionally, apply metadata filters.
        """
        try:

            print("\nWeaviate Query Details:")
            print(f"  Folder Id: {folder_id}")
            print(f"  Query: {query[:100]}...")
            print(f"  k: {k}")
            print(f"  Filters: {filters}")
            weaviate_response = []

            folder_id = sanitize_class_name(str(folder_id))  # type:ignore
            question_embedding = await self.generate_embedding(query)
            print(f"  Question Embedding Dimensions: {len(question_embedding)}")

            print("\nExecuting query...")
            collection = self.client.collections.get(str(folder_id))
            response = collection.query.hybrid(
                query=query,
                alpha=0.5,
                vector=question_embedding,
                return_metadata=MetadataQuery(score=True),
                limit=k,
                return_properties=["text"],
                return_references=[
                    QueryReference(
                        link_on="metadata",
                        return_properties=[
                            "filename",
                            "page_number",
                            "unique_id",
                            "last_modified",
                            "filetype",
                            "file_directory",
                            "source",
                            "languages",
                        ],
                    )
                ],
            )

            passed_response = response.objects
            documents = [
                {
                    "text": doc.properties.get("text"),
                    "metadata": doc.metadata,
                    "certainty": doc.metadata.score,
                    "filename": doc.references.get("filename"),
                }
                for doc in passed_response
            ]

            response = await self.rerank(query, documents)
            for result in response:
                weaviate_response.append(result)

            return weaviate_response
        except Exception as e:
            error_msg = f"Error querying folder '{folder_id}': {str(e)}"
            print(f"\nError in query_collection:")
            print(f"  {error_msg}")
            logging.error(error_msg)
            raise

    def delete_embeddings(self, folder_id: UUID, file_name: str):
        try:
            print("in delete embeddings.")
            folder_id = sanitize_class_name(str(folder_id))  # type:ignore

            collection = self.client.collections.get(str(folder_id))
            response = collection.query.fetch_objects(
                filters=Filter.by_property("filename").equal("file_name")
            )

            object_ids = [obj.uuid for obj in response.objects]
            print(f"Found objects: {object_ids}")
            for _uuid in object_ids:
                collection.data.delete_by_id(_uuid)
                print(f"Deleted object with UUID: {_uuid}")
            return "Deleted embeddings"
        except Exception as e:
            error_msg = f"Error deleting embeddings in folder '{folder_id}: {str(e)}"
            print(f"\nError in delete_embeddings:")
            print(f"  {error_msg}")
            logging.error(error_msg)
            raise
