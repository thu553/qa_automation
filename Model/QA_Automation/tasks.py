import aiomysql
import logging
import asyncio
import sys
import os
import redis
from celery_config import app
from utils import db_config, get_app_state, state, AppState, fine_tune_phobert, update_embeddings_after_finetune, load_data_db
from sentence_transformers import SentenceTransformer

# Thêm thư mục dự án vào sys.path
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Cấu hình logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

async def init_worker_pool():
    try:
        pool = await aiomysql.create_pool(**db_config)
        logger.info("Celery worker MySQL pool initialized")
        return pool
    except Exception as e:
        logger.error(f"Error creating worker MySQL pool: {str(e)}")
        raise

async def close_db_pool(pool):
    if pool:
        try:
            pool.close()
            await pool.wait_closed()
            logger.info("Celery worker MySQL pool closed")
        except Exception as e:
            logger.error(f"Error closing worker MySQL pool: {str(e)}")

def load_or_download_phobert(model_path="./phobert_base"):
    """Tải hoặc tải xuống và lưu mô hình PhoBERT với Sentence Transformers."""
    try:
        if not os.path.exists(model_path):
            logger.info(f"Directory {model_path} does not exist, creating and downloading PhoBERT...")
            os.makedirs(model_path, exist_ok=True)
            model = SentenceTransformer("vinai/phobert-base")
            model.save(model_path)
            logger.info(f"Model saved to {model_path}")
        else:
            logger.info(f"Loading PhoBERT from {model_path}")
            model = SentenceTransformer(model_path)
        return model, None  # Không cần tokenizer riêng
    except Exception as e:
        logger.error(f"Error loading or downloading PhoBERT: {str(e)}")
        raise

@app.task(bind=True, max_retries=3, retry_backoff=True)
def fine_tune_task(self):
    loop = None
    state = get_app_state()
    try:
        logger.info("Starting fine_tune_task")
        if state.redis_client is None:
            logger.info("Initializing redis_client for worker")
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            state.redis_client = redis.Redis.from_url(redis_url)
            state.redis_client.ping()
            logger.info("Redis client initialized successfully")

        if state.db_pool is None:
            logger.info("Initializing db_pool for worker")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            state.db_pool = loop.run_until_complete(init_worker_pool())
            logger.info("Database pool initialized successfully")

        # Tải hoặc tải xuống mô hình PhoBERT
        model_path = os.getenv("MODEL_PATH", "./phobert_base")
        state.model, state.tokenizer = load_or_download_phobert(model_path)

        loop = loop or asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        state.raw_data = loop.run_until_complete(load_data_db(state))
        # if state.raw_data.empty or len(state.raw_data) < 10:
        #     logger.warning("Insufficient data for fine-tuning, skipping")
        #     return False

        # thư hiêện fine_tune_phobert trả về 1 bool
        if not fine_tune_phobert(state, loop=loop):
            logger.error("fine_tune_phobert failed")
            raise Exception("Fine-tuning failed")

        logger.info("fine_tune_task completed successfully")
        update_embeddings_task.delay()
        return True

    except Exception as e:
        logger.error(f"Error in fine_tune_task: {str(e)}", exc_info=True)
        raise self.retry(exc=e, countdown=60)

    finally:
        if state.db_pool and loop:
            try:
                loop.run_until_complete(close_db_pool(state.db_pool))
                logger.info("Closed db pool in fine_tune_task")
            except Exception as e:
                logger.error(f"Error closing db_pool: {str(e)}")
            finally:
                state.db_pool = None
                if not loop.is_closed():
                    loop.close()
                    logger.info("Closed event loop in fine_tune_task")
        elif state.db_pool:
            logger.warning("db_pool exists but no loop, skipping close")

@app.task(bind=True, max_retries=3, retry_backoff=True)
def update_embeddings_task(self):
    loop = None
    state = get_app_state()
    try:
        logger.info("Starting update_embeddings_task")
        if state.redis_client is None:
            logger.info("Initializing redis client for worker")
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            state.redis_client = redis.Redis.from_url(redis_url)
            state.redis_client.ping()
            logger.info("Redis client initialized successfully")

        if state.db_pool is None:
            logger.info("Initializing db pool for worker")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            state.db_pool = loop.run_until_complete(init_worker_pool())
            logger.info("Database pool initialized successfully")

        model_path = os.getenv("CHECKPOINT_PATH", "./phobert_finetuned")
        if not os.path.exists(model_path):
            logger.warning(f"Checkpoint path {model_path} not found, falling back to {os.getenv('MODEL_PATH', './phobert_base')}")
            model_path = os.getenv("MODEL_PATH", "./phobert_base")
        state.model, state.tokenizer = load_or_download_phobert(model_path)

        loop = loop or asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(update_embeddings_after_finetune(state))
        logger.info("update_embeddings_task completed successfully")

    except Exception as e:
        logger.error(f"Update embeddings task failed: {str(e)}", exc_info=True)
        raise self.retry(exc=e, countdown=60)

    finally:
        if state.db_pool and loop:
            try:
                loop.run_until_complete(close_db_pool(state.db_pool))
                logger.info("Closed db pool in update_embeddings_task")
            except Exception as e:
                logger.error(f"Error closing db_pool: {str(e)}")
            finally:
                state.db_pool = None
                if not loop.is_closed():
                    loop.close()
                    logger.info("Closed event loop in update_embeddings_task")
        elif state.db_pool:
            logger.warning("db_pool exists but no loop, skipping close")