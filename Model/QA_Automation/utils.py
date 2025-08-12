import logging
import numpy as np
import pandas as pd
import faiss
import pickle
import asyncio
import redis
import aiomysql
import os
import re
import time
import psutil
import tempfile
import shutil
from redis.lock import Lock
from datetime import datetime
from typing import List, Tuple
from pyvi import ViTokenizer
from fastapi import HTTPException
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
from transformers import AutoTokenizer
from tenacity import retry, stop_after_attempt, wait_fixed

# Tắt cảnh báo pin_memory
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="torch.utils.data.dataloader")

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

# Đường dẫn lưu cache
CACHE_PATH = os.getenv("CACHE_PATH", "embedding_cache.pkl")
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "qa_index.faiss")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "phobert_base") if os.getenv("RENDER_ENV") != "production" else "/app/data/phobert_base"
CHECKPOINT_PATH = os.path.join(os.path.dirname(__file__), "phobert_finetuned") if os.getenv("RENDER_ENV") != "production" else "/app/data/phobert_finetuned"

# Hằng số
FINE_TUNE_THRESHOLD = 50
FINE_TUNE_INTERVAL = 3600  # 1 giờ

# Cấu hình MySQL cho aiomysql
db_config = {
    "host": os.getenv("MYSQLHOST", "localhost"),
    "port": int(os.getenv("MYSQLPORT", 3306)),
    "user": os.getenv("MYSQLUSER", "root"),
    "password": os.getenv("MYSQLPASSWORD", ""),
    "db": os.getenv("MYSQLDATABASE", "qa_db"),
    "maxsize": 20,
    "minsize": 10,
    "connect_timeout": 10,
    "charset": "utf8mb4"
}

# Quản lý trạng thái ứng dụng
class AppState:
    def __init__(self):
        self.raw_data = None
        self.cache_data = {
            'ids': [],
            'embeddings': np.array([]),
            'questions': [],
            'answers': [],
            'clean_questions': [],
            'clean_answers': [],
            'last_updated': None
        }
        self.index = None
        self.model = None
        self.last_fine_tune = 0
        self.last_fine_tune_record_count = 0
        self.db_pool = None
        self.redis_client = None
        self.tokenizer = None
        self.auto_fine_tune_enabled = True

# Khởi tạo state global
state = AppState()

def get_app_state():
    return state

# Khởi tạo connection pool và Redis client
async def init_db_pool(state: AppState):
    try:
        logger.debug(f"Attempting to create MySQL connection pool with config: {db_config}")
        state.db_pool = await aiomysql.create_pool(**db_config)
        logger.debug("MySQL connection pool created successfully")
    except aiomysql.Error as e:
        logger.error(f"MySQL connection error: {e}")
        raise RuntimeError(f"MySQL connection failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        logger.debug(f"Attempting to connect to Redis with URL: {redis_url}")
        state.redis_client = redis.Redis.from_url(redis_url)
        state.redis_client.ping()
        logger.debug("Redis client connected successfully")
    except redis.RedisError as e:
        logger.error(f"Redis error: {e}")
        raise HTTPException(status_code=500, detail=f"Redis error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    logger.info("MySQL connection pool and Redis client initialized successfully")

# Đóng connection pool và Redis client
async def close_db_state(state: AppState):
    try:
        if state.db_pool:
            state.db_pool.close()
            await state.db_pool.wait_closed()
            logger.info("MySQL connection pool closed")
        if state.redis_client:
            state.redis_client.close()
            logger.info("Redis client closed")
    except Exception as e:
        logger.error(f"Error closing resources: {e}")

# Khởi tạo bảng
async def init_db(state: AppState):
    async with state.db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            try:
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS qa_data (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        date DATETIME NOT NULL,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        embedding BLOB,
                        INDEX idx_date (date)
                    )
                """)
                await conn.commit()
                logger.info("Database initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing database: {e}")
                raise HTTPException(status_code=500, detail=f"Error initializing database: {str(e)}")

# Hàm làm sạch văn bản
def clean_text(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        return ""
    text = text.lower().strip()
    text = re.sub(r'[!?]{2,}', '.', text)  # Chuẩn hóa dấu câu
    text = re.sub(r'[^\w\s?.!]', '', text)  # Loại ký tự đặc biệt
    stop_words = {"chào", "dạ", "ạ", }
    text = ' '.join(word for word in ViTokenizer.tokenize(text).split() if word not in stop_words)
    return text

# Đếm số bản ghi
async def count_records(state: AppState) -> int:
    async with state.db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            try:
                await cursor.execute("SELECT COUNT(*) FROM qa_data")
                count = (await cursor.fetchone())[0]
                return count
            except Exception as e:
                logger.error(f"Error: {e}")
                return 0

# Lấy timestamp mới nhất
async def get_latest_timestamp(state: AppState) -> datetime:
    async with state.db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            try:
                await cursor.execute("SELECT MAX(date) FROM qa_data")
                result = (await cursor.fetchone())[0]
                return result if result else datetime.min
            except Exception as e:
                logger.error(f"Error getting latest timestamp: {e}")
                return datetime.min

# Đọc dữ liệu từ MySQL
async def load_data_db(state: AppState, limit: int = None, batch_size: int = 1000) -> pd.DataFrame:
    try:
        async with state.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = "SELECT id, date, question, answer, embedding FROM qa_data"
                if limit:
                    query += f" LIMIT {limit}"
                await cursor.execute(query)
                rows = await cursor.fetchall()
                if not rows:
                    logger.info("No data found in qa_data table")
                    return pd.DataFrame(columns=['id', 'date', 'question', 'answer', 'embedding'])
                data = []
                for row in rows:
                    embedding = np.frombuffer(row[4]) if row[4] else None
                    data.append({
                        'id': row[0],
                        'date': row[1],
                        'question': row[2],
                        'answer': row[3],
                        'embedding': embedding
                    })
                result = pd.DataFrame(data)
                logger.info(f"Loaded {len(result)} records from database")
                return result
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return pd.DataFrame(columns=['id', 'date', 'question', 'answer', 'embedding'])

# Lưu dữ liệu vào MySQL
async def save_data_batch(records: List[Tuple], state: AppState) -> List[Tuple[int, str, str]]:
    if not all(len(record) == 4 for record in records):
        logger.error("Invalid record format in records")
        raise HTTPException(status_code=400, detail="Each record must have 4 elements: "
                                                    "date, question, answer, embedding")
    async with state.db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            try:
                query = "INSERT INTO qa_data (date, question, answer, embedding) VALUES (%s, %s, %s, %s)"
                await cursor.executemany(query, records)
                await conn.commit()
                last_id = cursor.lastrowid
                logger.info(f"Saved {len(records)} records starting with ID: {last_id}")
                return [(last_id + i, record[1], record[2]) for i, record in enumerate(records)]
            except Exception as e:
                logger.error(f"Error saving data: {e}")
                raise HTTPException(status_code=500, detail="Lỗi lưu dữ liệu")

# Mã hóa văn bản
def encode_text_batch(texts: List[str], state: AppState) -> np.ndarray:
    if not texts:
        return np.array([])
    embeddings = state.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    if embeddings.size > 0:
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    return embeddings

# Lưu FAISS index với Redis Lock
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def save_faiss_index(index, path: str, redis_client: redis.Redis):
    with Lock(redis_client, "faiss_index_lock", timeout=120, blocking_timeout=20):
        try:
            start_time = time.time()
            faiss.write_index(index, path)
            logger.info(f"Saved FAISS index to {path} in {time.time() - start_time:.2f} seconds")
        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}")
            raise

# Lưu cache với Redis Lock
def save_cache(cache_data, path: str, redis_client: redis.Redis):
    with Lock(redis_client, "cache_lock", timeout=60, blocking_timeout=10):
        try:
            with open(path, "wb") as f:
                pickle.dump(cache_data, f)
            logger.info(f"Saved cache to {path}")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
            raise

# Kiểm tra tài nguyên
def check_resources() -> bool:
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    logger.info(f"System resources: CPU {cpu_percent}%, Memory {memory.percent}%")
    if cpu_percent > 70 or memory.percent > 70:
        logger.warning("Insufficient system resources, postponing fine-tuning")
        return False
    return True

# Tải hoặc tạo embedding
async def initialize_cache_and_index(state: AppState):
    try:
        if os.path.exists(CACHE_PATH):
            with open(CACHE_PATH, "rb") as f:
                state.cache_data = pickle.load(f)
            logger.info(f"Loaded {len(state.cache_data['ids'])} embeddings from cache")
        db_count = await count_records(state)
        db_latest = await get_latest_timestamp(state)
        if len(state.cache_data['ids']) != db_count or (state.cache_data['last_updated'] and state.cache_data['last_updated'] < db_latest):
            logger.warning("Cache outdated or mismatched, regenerating")
            state.raw_data = await load_data_db(state)
            clean_questions = [clean_text(q) for q in state.raw_data['question'] if q]
            clean_answers = [clean_text(a) for a in state.raw_data['answer'] if a]
            state.cache_data = {
                'ids': state.raw_data['id'].tolist(),
                'embeddings': encode_text_batch(clean_questions, state),
                'questions': state.raw_data['question'].tolist(),
                'answers': state.raw_data['answer'].tolist(),
                'clean_questions': clean_questions,
                'clean_answers': clean_answers,
                'last_updated': db_latest
            }
            save_cache(state.cache_data, CACHE_PATH, state.redis_client)
        logger.info(f"Cache contains {len(state.cache_data['ids'])} embeddings")
    except Exception as e:
        logger.error(f"Error initializing cache: {e}")
        state.cache_data = {
            'ids': [],
            'embeddings': np.array([]),
            'questions': [],
            'answers': [],
            'clean_questions': [],
            'clean_answers': [],
            'last_updated': None
        }

    dimension = state.cache_data['embeddings'].shape[1] if state.cache_data['embeddings'].size else 768
    state.index = faiss.IndexIDMap(faiss.IndexFlatL2(dimension))
    if state.cache_data['embeddings'].size and state.cache_data['ids']:
        state.index.add_with_ids(
            state.cache_data['embeddings'].astype(np.float32),
            np.array(state.cache_data['ids'], dtype=np.int64)
        )
    try:
        save_faiss_index(state.index, FAISS_INDEX_PATH, state.redis_client)
        logger.info("FAISS index saved")
    except Exception as e:
        logger.error(f"Error saving FAISS index: {e}")
    try:
        state.index = faiss.read_index(FAISS_INDEX_PATH)
        logger.info("FAISS index loaded")
    except Exception as e:
        logger.warning(f"No FAISS index found, using fresh one: {e}")
        state.index = faiss.IndexIDMap(faiss.IndexFlatL2(dimension))

# Hàm cập nhật embedding sau fine-tune
async def update_embeddings_after_finetune(state: AppState):
    state.raw_data = await load_data_db(state)
    batch_size = 1000
    clean_questions = [clean_text(q) for q in state.raw_data['question'] if q]
    clean_answers = [clean_text(a) for a in state.raw_data['answer'] if a]
    new_embeddings = state.model.encode(clean_questions, convert_to_numpy=True, show_progress_bar=True)
    if new_embeddings.size > 0:
        new_embeddings = new_embeddings / np.linalg.norm(new_embeddings, axis=1, keepdims=True)
    state.cache_data = {
        'ids': state.raw_data['id'].tolist(),
        'embeddings': new_embeddings,
        'questions': state.raw_data['question'].tolist(),
        'answers': state.raw_data['answer'].tolist(),
        'clean_questions': clean_questions,
        'clean_answers': clean_answers,
        'last_updated': datetime.now()
    }
    async with state.db_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            try:
                for i in range(0, len(state.cache_data['ids']), batch_size):
                    batch_ids = state.cache_data['ids'][i:i + batch_size]
                    batch_embs = state.cache_data['embeddings'][i:i + batch_size]
                    query = "UPDATE qa_data SET embedding = %s WHERE id = %s"
                    await cursor.executemany(query, [(emb.tobytes(), id_) for emb, id_ in zip(batch_embs, batch_ids)])
                    await conn.commit()
                logger.info("Updated embeddings in database")
            except Exception as e:
                logger.error(f"Error updating embeddings: {e}")
                raise
    dimension = state.cache_data['embeddings'].shape[1] if state.cache_data['embeddings'].size else 768
    state.index = faiss.IndexIDMap(faiss.IndexFlatL2(dimension))
    if state.cache_data['embeddings'].size:
        state.index.add_with_ids(
            state.cache_data['embeddings'].astype(np.float32),
            np.array(state.cache_data['ids'], dtype=np.int64)
        )
    save_cache(state.cache_data, CACHE_PATH, state.redis_client)
    save_faiss_index(state.index, FAISS_INDEX_PATH, state.redis_client)
    logger.info("Updated embeddings and FAISS index after fine-tuning")

# Hàm fine-tune PhoBERT
def fine_tune_phobert(state: AppState, loop: asyncio.AbstractEventLoop = None) -> bool:
    logger.info("Starting fine_tune_phobert")
    start_time = time.time()

    if not check_resources():
        logger.error("Insufficient system resources for fine-tuning")
        return False

    if state.model is None:
        logger.error("Model not initialized")
        return False

    #  kiêm tra và tải dữ liệu thô nếu không đủ 10 ban ghji thì false
    try:
        if state.raw_data is None or state.raw_data.empty or len(state.raw_data) < 10:
            loop = loop or asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                state.raw_data = loop.run_until_complete(load_data_db(state))
            finally:
                if not loop.is_closed():
                    loop.close()
            if len(state.raw_data) < 10:
                logger.error("Not enough data for fine-tuning")
                return False

        # Khởi tạo tokenizer
        base_path = os.getenv("MODEL_PATH", MODEL_PATH)
        logger.info(f"Loading tokenizer from: {base_path}")
        # Kiểm tra file tokenizer (tokenizer_config.json) tồn tại không, nếu không thì dừng
        if base_path.endswith("phobert_base") and not os.path.exists(os.path.join(base_path, "tokenizer_config.json")):
            logger.error(f"Tokenizer config not found in {base_path}. Required files: tokenizer_config.json, vocab.txt, bpe.codes")
            return False
        # nếu tồn tại nhng none, tải từ base_path và lưu vào state.tokenizer
        if state.tokenizer is None:
            state.tokenizer = AutoTokenizer.from_pretrained(
                base_path,
                use_fast=False,
                trust_remote_code=True
            )
            logger.info("Initialized PhoBERT tokenizer")

        with Lock(state.redis_client, "fine_tune_lock", timeout=3600, blocking_timeout=60):
            try:
                train_examples = []
                #  thm dữ lệu vào train_examples
                for _, row in state.raw_data.iterrows():
                    q_clean = clean_text(str(row['question']))
                    a_clean = clean_text(str(row['answer']))
                    if q_clean and a_clean:
                        train_examples.append(InputExample(texts=[q_clean, a_clean]))

                # nhóm các câu hỏi theo câu trả lời
                groups = state.raw_data.groupby('answer')
                # lấy các câu hoỏi trong cùng 1 nhóm, tạo cặp câu hỏi tương tự nếu nhóm có nhiều hơn 1 câu.
                for answer, group in groups:
                    clean_questions = [clean_text(q) for q in group['question'].tolist() if clean_text(q)]
                    if len(clean_questions) > 1:
                        for i in range(len(clean_questions)):
                            for j in range(i + 1, len(clean_questions)):
                                train_examples.append(InputExample(texts=[clean_questions[i], clean_questions[j]]))

                # Kiểm tra nếu train_examples rỗng, dừng nếu không có dữ liệu.
                if not train_examples:
                    logger.error("No valid training examples")
                    return False

                train_dataloader = DataLoader( #chia train_examples thành lô (batch size 4), xáo trộn để học đều.
                    train_examples,
                    shuffle=True,
                    batch_size=4,
                    pin_memory=False
                )
                # đo sai số khi huấn luyện
                train_loss = losses.MultipleNegativesRankingLoss(state.model)
                # xác ịnh nơi lưu mô hình
                checkpoint_path = os.getenv("CHECKPOINT_PATH", CHECKPOINT_PATH)

                # Tạo thư mục tạm (temp_dir) để lưu mô hình trong quá trình huấn luyện
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_checkpoint = os.path.join(temp_dir, "phobert_temp")
                    logger.info(f"Using temporary checkpoint: {temp_checkpoint}")
                    # Xóa mô hình cũ tại checkpoint_path nếu tồn tại.
                    if os.path.exists(checkpoint_path):
                        logger.info(f"Removing old checkpoint at {checkpoint_path}")
                        shutil.rmtree(checkpoint_path, ignore_errors=True)

                    # state.model.fit 3 lần
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            state.model.fit(
                                train_objectives=[(train_dataloader, train_loss)],
                                epochs=1,
                                warmup_steps=100,
                                output_path=temp_checkpoint,
                                checkpoint_path=temp_checkpoint,
                                checkpoint_save_steps=100,
                                show_progress_bar=True # hển th tiê đọ
                            )
                            break
                        except Exception as e:
                            logger.warning(f"Attempt {attempt + 1} failed: {e}")
                            if attempt == max_retries - 1:
                                logger.error(f"Fine-tuning failed after {max_retries} retries")
                                return False
                            time.sleep(5)

                    # di chuyêển mô hình từ thư mục tạm sang checkpoint_path
                    shutil.move(temp_checkpoint, checkpoint_path)
                    logger.info(f"Moved fine-tuned model to {checkpoint_path}")

                if not os.path.exists(checkpoint_path):
                    logger.error(f"Checkpoint not found: {checkpoint_path}")
                    return False

                # Tải lại mô hình từ checkpoint_path vào state.model
                state.model = SentenceTransformer(checkpoint_path)
                logger.info("Reloaded fine-tuned model")
                # Cập nhật thời gian
                state.last_fine_tune = int(time.time())
                loop = loop or asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # Cập nhật ố bản ghi cho lần fine tune
                    state.last_fine_tune_record_count = loop.run_until_complete(count_records(state))
                finally:
                    if not loop.is_closed():
                        loop.close()
                        logger.info("Closed temporary event loop")

                logger.info(f"Fine-tuning completed in {time.time() - start_time:.2f}s")
                return True

            except Exception as e:
                logger.error(f"Error during fine-tuning: {e}", exc_info=True)
                return False

    except Exception as e:
        logger.error(f"Fine-tune error: {e}")
        return False