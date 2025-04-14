import logging
import time
import os
from typing import List
import numpy as np
from collections import defaultdict
from multiprocessing.pool import Pool
from pymilvus import Collection, DataType, MilvusClient, connections

from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai.chat_models import ChatOpenAI

from arklex.env.prompts import load_prompts
from arklex.utils.mysql import mysql_pool
from arklex.utils.model_config import MODEL
from arklex.env.prompts import load_prompts
from arklex.utils.graph_state import MessageState
from arklex.env.tools.RAG.retrievers.retriever_document import RetrieverDocument, RetrieverDocumentType, RetrieverResult, embed, embed_retriever_document

EMBED_DIMENSION = 1536
MAX_TEXT_LENGTH = 65535
CHUNK_NEIGHBOURS = 3

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class RetrieveEngine():
    @staticmethod
    def milvus_retrieve(state: MessageState):
        # get the input message
        user_message = state['user_message']

        # Search for the relevant documents
        milvus_retriever = MilvusRetrieverExecutor(state["bot_config"])
        retrieved_text, retriever_params = milvus_retriever.retrieve(user_message.history)

        state["message_flow"] = retrieved_text
        state["metadata"]["tool_response"] = retriever_params
        return state

class MilvusRetriever:
    def __enter__(self):
        self.uri = os.getenv("MILVUS_URI", "")
        self.token = os.getenv("MILVUS_TOKEN", "")
        self.client = MilvusClient(uri=self.uri, token=self.token)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.client.close()

    def get_bot_uid(self, bot_id: str, version: str):
        return f"{bot_id}__{version}"

    def create_collection_with_partition_key(self, collection_name: str):
        schema = MilvusClient.create_schema(
            auto_id=False,
            enable_dynamic_field=True,
            partition_key_field="bot_uid",
            num_partitions=16,
        )
        schema.add_field(
            field_name="id", datatype=DataType.VARCHAR, is_primary=True, max_length=100
        )
        schema.add_field(
            field_name="qa_doc_id", datatype=DataType.VARCHAR, max_length=40
        )
        schema.add_field(
            field_name="bot_uid", datatype=DataType.VARCHAR, max_length=100
        )
        schema.add_field(field_name="chunk_id", datatype=DataType.INT32)
        schema.add_field(
            field_name="qa_doc_type", datatype=DataType.VARCHAR, max_length=10
        )
        schema.add_field(field_name="metadata", datatype=DataType.JSON)
        schema.add_field(
            field_name="text", datatype=DataType.VARCHAR, max_length=MAX_TEXT_LENGTH
        )
        schema.add_field(
            field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=EMBED_DIMENSION
        )
        schema.add_field(field_name="timestamp", datatype=DataType.INT64)
        # schema.add_field(field_name="num_tokens", datatype=DataType.INT64)
        index_params = self.client.prepare_index_params()
        index_params.add_index(field_name="id")
        index_params.add_index(field_name="qa_doc_id")
        index_params.add_index(field_name="bot_uid")
        index_params.add_index(
            field_name="embedding", index_type="FLAT", metric_type="L2"
        )

        self.client.create_collection(
            collection_name=collection_name, schema=schema, index_params=index_params
        )

    def delete_documents_by_qa_doc_id(self, collection_name: str, qa_doc_id: str):
        logger.info(
            f"Deleting vector db documents by qa_doc_id: {qa_doc_id} from collection: {collection_name}"
        )
        res = self.client.delete(
            collection_name=collection_name, filter=f"qa_doc_id=='{qa_doc_id}'"
        )
        return res
    
    def add_documents_dicts(
        self, documents: List[dict], collection_name: str, upsert: bool = False
    ):
        logger.info(f"Celery sub task for adding {len(documents)} documents to collection: {collection_name}.")
        retriever_documents = [RetrieverDocument.from_dict(doc) for doc in documents]
        documents_to_insert = []

        if not upsert:
            # check if the document already exists in the collection
            for doc in retriever_documents:
                res = self.client.get(collection_name=collection_name, ids=doc.id)
                if len(res) == 0:
                    documents_to_insert.append(doc)
            logger.info(f"Exisiting documents: {len(documents_to_insert)}")
        else:
            documents_to_insert = retriever_documents

        res = []
        for doc in documents_to_insert:
            data = doc.to_milvus_schema_dict_and_embed()
            try:
                res.append(
                    self.client.upsert(collection_name=collection_name, data=[data])
                )
            except Exception as e:
                logger.error(f"Error adding document id: {data['id']} error: {e}")
                raise e
        return res
    
    def add_documents_parallel(
        self, collection_name: str, bot_id: str, version: str, documents: List[RetrieverDocument], process_pool: Pool, upsert: bool = False
    ):
        logger.info(
            f"Adding {len(documents)} vector db documents to collection '{collection_name}' for bot_id: {bot_id} version: {version}"
        )
        if not self.client.has_collection(collection_name):
            logger.info(f"No collection found hence creating collection: {collection_name}")
            self.create_collection_with_partition_key(collection_name)

        documents_to_insert = []

        if not upsert:
            # check if the document already exists in the collection
            for doc in documents:
                res = self.client.get(collection_name=collection_name, ids=doc.id)
                if len(res) == 0:
                    documents_to_insert.append(doc)
            logger.info(f"Exisiting documents: {len(documents_to_insert)}")
        else:
            documents_to_insert = documents

        res = []
        # process 100 documents at a time
        count = 0
        for i in range(0, len(documents_to_insert), 100):
            batch_docs = documents_to_insert[i:i+100]
            embedded_batch_docs = process_pool.map(embed_retriever_document, batch_docs)

            res.extend(
                self.client.upsert(collection_name=collection_name, data=embedded_batch_docs)
            )
            count += len(batch_docs)
            logger.info(f"Added {count}/{len(documents_to_insert)} docs")

        return res
        
    def add_documents(
        self, collection_name: str, bot_id: str, version: str, documents: List[RetrieverDocument], upsert: bool = False
    ):
        logger.info(
            f"Adding {len(documents)} vector db documents to collection {collection_name} for bot_id: {bot_id} version: {version}"
        )

        if not self.client.has_collection(collection_name):
            self.create_collection_with_partition_key(collection_name)

        documents_to_insert = []

        if not upsert:
            # check if the document already exists in the collection
            for doc in documents:
                res = self.client.get(collection_name=collection_name, ids=doc.id)
                if len(res) == 0:
                    documents_to_insert.append(doc)
            logger.info(f"Exisiting documents: {len(documents_to_insert)}")
        else:
            documents_to_insert = documents

        res = []
        for doc in documents_to_insert:
            data = doc.to_milvus_schema_dict_and_embed()
            try:
                res.append(
                    self.client.upsert(collection_name=collection_name, data=[data])
                )
            except Exception as e:
                logger.error(f"Error adding document id: {data['id']} error: {e}")
                raise e
        return res

    def search(self, collection_name: str, bot_id: str, version: str, query: str, top_k: int = 4) -> List[RetrieverResult]:
        logger.info(
            f"Retreiver search for query: {query} on collection {collection_name} for bot_id: {bot_id} version: {version}"
        )
        
        partition_key = self.get_bot_uid(bot_id, version)
        query_embedding = embed(query)
        res = self.client.search(
            collection_name=collection_name,
            data=[query_embedding],
            limit=top_k,
            filter=f"bot_uid == '{partition_key}'",
            output_fields=["qa_doc_id", "chunk_id", "qa_doc_type", "metadata", "text"],
        )

        ret_results: List[RetrieverResult] = []
        for r in res[0]:
            logger.info(f"Milvus search result: {r}")
            qa_doc_id = r["entity"]["qa_doc_id"]
            chunk_id = r["entity"]["chunk_id"]
            text = r["entity"]["text"]
            logger.info(f"Retrieved qa_doc_id: {qa_doc_id} chunk_id: {chunk_id}")

            ret_results.append(RetrieverResult(
                qa_doc_id=qa_doc_id,
                qa_doc_type=RetrieverDocumentType(r["entity"]["qa_doc_type"]),
                text=text,
                metadata=r["entity"]["metadata"],
                distance=r["distance"],
                start_chunk_idx=chunk_id,
                end_chunk_idx=chunk_id,
            ))

        return ret_results

    ## TODO: get num_tokens for functions inside milvus_retriever.py and retriever_document.py (with classmethod RetrieverDocument.faq_retreiver_doc); influence token migrations
    def get_qa_docs(
        self, collection_name: str, bot_id: str, version: str, qa_doc_type: RetrieverDocumentType
    ) -> List[RetrieverDocument]:
        connections.connect(
            uri=self.uri,
            token=self.token,
        )
        collection = Collection(collection_name)

        partition_key = self.get_bot_uid(bot_id, version)
        iterator = collection.query_iterator(
            batch_size=1000,
            expr=f"qa_doc_type=='{qa_doc_type.value}' and bot_uid=='{partition_key}'",
            output_fields=[
                "id",
                "qa_doc_id",
                "chunk_id",
                "qa_doc_type",
                "text",
                "metadata",
                "bot_uid",
                "timestamp",
            ],
        )

        qa_docs = []
        qa_doc_map = defaultdict(list)
        while True:
            result = iterator.next()
            if len(result) == 0:
                iterator.close()
                break

            for r in result:
                if qa_doc_type == RetrieverDocumentType.FAQ:
                    qa_doc = RetrieverDocument.faq_retreiver_doc(
                        id=r["id"], text=r["text"], metadata=r["metadata"], bot_uid=r["bot_uid"], timestamp=r["timestamp"]
                    )
                    qa_docs.append(qa_doc)
                else:
                    qa_doc_map[r["qa_doc_id"]].append(r)
                    qa_doc = RetrieverDocument(
                        r["id"],
                        r["qa_doc_id"],
                        r["chunk_id"],
                        qa_doc_type,
                        r["text"],
                        r["metadata"],
                        is_chunked=True,
                        bot_uid=r["bot_uid"],
                        embedding=None,
                        timestamp=r["timestamp"],
                    )

        if qa_doc_type != RetrieverDocumentType.FAQ:
            for qa_doc_id, docs in qa_doc_map.items():
                sorted_docs = sorted(docs, key=lambda x: x["chunk_id"])
                txt = "".join([d["text"] for d in sorted_docs])
                ret_doc = RetrieverDocument.unchunked_retreiver_doc(
                    qa_doc_id,
                    qa_doc_type,
                    txt,
                    sorted_docs[0]["metadata"],
                    sorted_docs[0]["bot_uid"],
                    sorted_docs[0]["timestamp"],
                )
                qa_docs.append(ret_doc)

        return qa_docs

    def get_qa_doc(
        self, collection_name: str, qa_doc_id: str
    ) -> RetrieverDocument:

        logger.info(f"Getting qa doc with id {qa_doc_id} from collection {collection_name}")
        res = self.client.query(
            collection_name=collection_name,
            filter=f"qa_doc_id=='{qa_doc_id}'",
            output_fields=[
                "qa_doc_id",
                "chunk_id",
                "qa_doc_type",
                "text",
                "metadata",
                "bot_uid",
                "timestamp",
            ],
        )

        if len(res) == 0:
            return None

        sorted_res = sorted(res, key=lambda x: x["chunk_id"])

        if sorted_res[0]["qa_doc_type"] == RetrieverDocumentType.FAQ.value:
            return RetrieverDocument.faq_retreiver_doc(
                id=sorted_res[0]["qa_doc_id"],
                text=sorted_res[0]["text"],
                metadata=sorted_res[0]["metadata"],
                bot_uid=sorted_res[0]["bot_uid"],
                timestamp=sorted_res[0]["timestamp"],
            )
        else:
            txt = "".join([d["text"] for d in sorted_res])
            return RetrieverDocument.unchunked_retreiver_doc(
                sorted_res[0]["qa_doc_id"],
                RetrieverDocumentType(sorted_res[0]["qa_doc_type"]),
                txt,
                sorted_res[0]["metadata"],
                sorted_res[0]["bot_uid"],
                sorted_res[0]["timestamp"],
            )

    def get_qa_doc_ids(
        self, collection_name: str, bot_id: str, version: str, qa_doc_type: RetrieverDocumentType
    ) -> List[dict]:
        logger.info(f"Getting all qa_doc_ids from collection '{collection_name}' for bot_id: {bot_id}, version: {version}")
        partition_key = self.get_bot_uid(bot_id, version)
        connections.connect(
            uri=self.uri,
            token=self.token,
        )
        collection = Collection(collection_name)

        iterator = collection.query_iterator(
            batch_size=1000,
            expr=f"qa_doc_type == '{qa_doc_type.value}' and bot_uid == '{partition_key}'",
            output_fields=["id", "qa_doc_id"],
        )

        qa_doc_ids = set()
        while True:
            result = iterator.next()
            if len(result) == 0:
                iterator.close()
                break

            for r in result:
                qa_doc_ids.add(r["qa_doc_id"])

        return list(qa_doc_ids)

    def has_collection(self, collection_name: str):
        return self.client.has_collection(collection_name)

    def load_collection(self, collection_name: str):
        if self.client.has_collection(collection_name):
            self.client.load_collection(collection_name)
            return
        else:
            raise ValueError(f"Milvus Collection {collection_name} does not exist")

    def release_collection(self, collection_name: str):
        return self.client.release_collection(collection_name)
    
    def drop_collection(self, collection_name: str):
        return self.client.drop_collection(collection_name)
    
    def get_all_vectors(self, collection_name: str):
        connections.connect(
            uri=self.uri,
            token=self.token,
        )
        collection = Collection(collection_name)

        iterator = collection.query_iterator(
            batch_size=16000,
            output_fields=[
                'id',
                'qa_doc_id',
                "chunk_id",
                "qa_doc_type",
                "num_tokens",
                "metadata", 
                "text",
                "embedding",
                "timestamp",
            ],
        )

        vectors = []
        count = 0
        while True:
            result = iterator.next()
            if len(result) == 0:
                iterator.close()
                break

            for r in result:
                vectors.append(r)
                count += 1
        
        logger.info(f"collection {collection_name} Total vectors: {count}")
        return vectors

    def add_vectors_parallel(
        self, collection_name: str, bot_id: str, version: str, vectors: List[dict], upsert: bool = False
    ):
        logger.info(
            f"Adding {len(vectors)} vector db documents to institution {collection_name} for bot_id: {bot_id} version: {version}"
        )
        if not self.client.has_collection(collection_name):
            logger.info(f"No colelction found hence creating collection: {collection_name}")
            self.create_collection_with_partition_key(collection_name)

        vectors_to_insert = []

        if not upsert:
            # check if the document already exists in the collection
            for vec in vectors:
                res = self.client.query(
                    collection_name=collection_name, 
                    ids=vec["id"], 
                )
                if len(res) == 0:
                    vectors_to_insert.append(vec)
            logger.info(f"New vectors to insert: {len(vectors_to_insert)}")
        else:
            vectors_to_insert = vectors
        
        for vec in vectors_to_insert:
            vec["bot_uid"] = self.get_bot_uid(bot_id, version)

        res = []
        # process 100 documents at a time
        count = 0
        for i in range(0, len(vectors_to_insert), 100):
            batch_vectors = vectors_to_insert[i:i+100]

            res.extend(
                self.client.upsert(collection_name=collection_name, data=batch_vectors)
            )
            count += len(batch_vectors)
            logger.info(f"{collection_name}: Added {count}/{len(vectors_to_insert)} docs")
        return res

    def is_collection_loaded(self, collection_name: str):
        state = self.client.get_load_state(collection_name)
        print("loaded state: ", state)
        if state["state"].__str__() == "Loaded":
            return True
        else:
            return False
        
    def delete_vectors_by_partition_key(self, collection_name: str, bot_id: str, version: str):
        partition_key = self.get_bot_uid(bot_id, version)
        res = self.client.delete(collection_name=collection_name, filter=f"bot_uid=='{partition_key}'")
        logger.info(f"Deleted {len(res)} vectors from collection {collection_name} for bot_id: {bot_id} version: {version}")

        # check if the collection is empty
        res = self.client.query(collection_name=collection_name, output_fields=["count(*)"])
        if res[0]["count(*)"] == 0:
            logger.info(f"Collection {collection_name} is empty.")

        return res

    def get_vector_count_for_bot(self, collection: str, bot_id: str, version: str):
        res = self.client.query(
            collection_name=collection,
            filter=f"bot_uid=='{bot_id}__{version}'"
            )
        return len(res)
    
    # def get_token_count_for_bot(self, collection_name: str, bot_id: str, version: str):
    #     logger.info(f"Counting tokens in collection {collection_name} for bot_id: {bot_id}, version: {version}")
    #     partition_key = self.get_bot_uid(bot_id, version)
    #     res = self.client.query(
    #         collection_name=collection_name,
    #         filter=f"bot_uid=='{partition_key}'",
    #         output_fields=["num_tokens"],
    #     )
    #     return sum([r.get("num_tokens", 0) for r in res])
    
    def get_collection_size(self, collection_name: str):
        # real time vector count for the collection
        return self.client.query(collection_name=collection_name, output_fields=["count(*)"])[0]["count(*)"]
    
    def migrate_vectors(self, old_collection_name: str, bot_id: str, version: str, new_collection_name: str):
        partition_key = self.get_bot_uid(bot_id, version)
        connections.connect(
            uri=self.uri,
            token=self.token,
        )
        collection = Collection(old_collection_name)

        iterator = collection.query_iterator(
            batch_size=16000,
            expr=f"bot_uid=='{partition_key}'",
            output_fields=[
                'id',
                'bot_uid',
                'qa_doc_id',
                "chunk_id",
                "num_tokens",
                "qa_doc_type",
                "metadata", 
                "text",
                "embedding",
                "timestamp",
            ],
        )

        vectors = []
        count = 0
        while True:
            result = iterator.next()
            if len(result) == 0:
                iterator.close()
                break

            for r in result:
                vectors.append(r)
                count += 1

        logger.info(f"migrating {count} vectors for bot {bot_id} version {version}")
        
        # add vectors to new collection
        if not self.has_collection(new_collection_name):
            logger.info(f"No collection found hence creating collection: {new_collection_name}")
            self.create_collection_with_partition_key(new_collection_name)
        self.add_vectors_parallel(new_collection_name, bot_id, version, vectors)

        # delete vectors from old collection
        self.delete_vectors_by_partition_key(old_collection_name, bot_id, version)
        
        logger.info(f"moved {count} vectors from {old_collection_name} to {new_collection_name}")
        return count

    def list_collections(self):
        return self.client.list_collections()


class MilvusRetrieverExecutor:
    def __init__(self, bot_config):
        self.bot_config = bot_config
        self.llm = ChatOpenAI(model=MODEL["model_type_or_path"], timeout=30000)

    def generate_thought(self, retriever_results: List[RetrieverResult]) -> str:
        # post process list of documents into str
        retrieved_str = ""
        for doc in retriever_results:
            if doc.metadata.get("title"):
                retrieved_str += "title: " + doc.metadata["title"] + "\n"
            if doc.metadata.get("source"):
                retrieved_str += "source: " + doc.metadata["source"] + "\n"
            retrieved_str += "content: " + doc.text + "\n\n"
        return retrieved_str

    def _gaussian_similarity(self, distance, sigma=0.5):
        similarity = np.exp(-(distance**2) / (2 * sigma**2)) * 100
        return round(float(similarity), 2)

    def postprocess(self, retriever_results: List[RetrieverResult]):
        retriever_returns = []
        for doc in retriever_results:
            confidence_score = self._gaussian_similarity(doc.distance)
            item = {
                "qa_doc_id": doc.qa_doc_id,
                "qa_doc_type": doc.qa_doc_type.value,
                "title": doc.metadata.get("title"),
                "content": doc.text,
                "source": doc.metadata.get("source"),
                "raw_score": round(float(doc.distance), 4),
                "confidence": confidence_score,
            }
            retriever_returns.append(item)
        return {"retriever": retriever_returns}

    def retrieve(self, chat_history_str):
        """Given a chat history, retrieve relevant information from the database."""
        st = time.time()
        prompts = load_prompts(self.bot_config)
        contextualize_q_prompt = PromptTemplate.from_template(
            prompts.get("retrieve_contextualize_q_prompt", "")
        )
        ret_input_chain = contextualize_q_prompt | self.llm | StrOutputParser()
        ret_input = ret_input_chain.invoke({"chat_history": chat_history_str})
        rit = time.time() - st

        ret_results: List[RetrieverResult] = []
        st = time.time()
        milvus_db = mysql_pool.fetchone("SELECT collection_name FROM qa_bot WHERE id=%s AND version=%s", (self.bot_config.bot_id, self.bot_config.version))
        with MilvusRetriever() as retriever:
            ret_results = retriever.search(milvus_db["collection_name"], self.bot_config.bot_id, self.bot_config.version, ret_input)
        rt = time.time() - st
        logger.info(f"MilvusRetriever search took {rt} seconds")
        retriever_params = self.postprocess(ret_results)
        retriever_params["timing"] = {"retriever_input": rit, "retriever_search": rt}
        thought = self.generate_thought(ret_results)
        return thought, retriever_params