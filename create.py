import os
import json
import argparse
import time
import logging
import subprocess
import signal
import atexit
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek

from arklex.utils.utils import init_logger
from arklex.orchestrator.orchestrator import AgentOrg
from arklex.orchestrator.generator.generator import Generator
from arklex.env.tools.RAG.build_rag import build_rag
from arklex.env.tools.database.build_database import build_database
from arklex.utils.model_config import MODEL

logger = init_logger(log_level=logging.INFO, filename=os.path.join(os.path.dirname(__file__), "logs", "arklex.log"))
load_dotenv()

# API_PORT = "55135"
# NLUAPI_ADDR = f"http://localhost:{API_PORT}/nlu"
# SLOTFILLAPI_ADDR = f"http://localhost:{API_PORT}/slotfill"

def generate_taskgraph(args):
    model = ChatDeepSeek(model=MODEL["model_type_or_path"], timeout=30000)
    generator = Generator(args, args.config, model, args.output_dir)
    taskgraph_filepath = generator.generate()
    # Update the task graph with the API URLs
    task_graph = json.load(open(os.path.join(os.path.dirname(__file__), taskgraph_filepath)))
    task_graph["nluapi"] = ""
    task_graph["slotfillapi"] = ""
    with open(taskgraph_filepath, "w") as f:
        json.dump(task_graph, f, indent=4)


def init_worker(args):
    ## TODO: Need to customized based on different use cases
    config = json.load(open(args.config))
    workers = config["workers"]
    worker_names = set([worker["name"] for worker in workers])
    if "FaissRAGWorker" in worker_names:
        logger.info("Initializing FaissRAGWorker...")
        # if url: uncomment the following line
        build_rag(args.output_dir, config["rag_docs"])
        # if shopify: uncomment the following lines
        # import shopify
        # from arklex.utils.loaders.shopify import ShopifyLoader
        # session = shopify.Session(os.environ["SHOPIFY_SHOP_URL"], os.environ["SHOPIFY_API_VERSION"], os.environ["SHOPIFY_ACCESS_TOKEN"])
        # shopify.ShopifyResource.activate_session(session)
        # loader = ShopifyLoader()
        # docs = loader.load()
        # filepath = os.path.join(args.output_dir, "documents.pkl")
        # ShopifyLoader.save(filepath, docs)
        # chunked_docs = loader.chunk(docs)
        # filepath_chunk = os.path.join(args.output_dir, "chunked_documents.pkl")
        # ShopifyLoader.save(filepath_chunk, chunked_docs)
        

    elif any(node in worker_names for node in ("DataBaseWorker", "search_show", "book_show", "check_booking", "cancel_booking")):
        logger.info("Initializing DataBaseWorker...")
        build_database(args.output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default="./arklex/orchestrator/examples/customer_service_config.json")
    parser.add_argument('--output-dir', type=str, default="./examples/test")
    parser.add_argument('--model', type=str, default=MODEL["model_type_or_path"])
    parser.add_argument('--log-level', type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    parser.add_argument('--task', type=str, choices=["gen_taskgraph", "init", "all"], default="all")
    args = parser.parse_args()
    MODEL["model_type_or_path"] = args.model
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logger = init_logger(log_level=log_level, filename=os.path.join(os.path.dirname(__file__), "logs", "arklex.log"))

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir, exist_ok=True)
    
    if args.task == "all":
        generate_taskgraph(args)
        init_worker(args)
    elif args.task == "gen_taskgraph":
        generate_taskgraph(args)
    elif args.task == "init":
        init_worker(args)