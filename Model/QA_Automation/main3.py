import logging
import numpy as np
import pandas as pd
import time
from io import BytesIO
import asyncio
from datetime import datetime
from typing import List, Dict
from fastapi import FastAPI, HTTPException, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from transformers import AutoModel, AutoTokenizer
from pandas import errors as pd_errors
import atexit
import os
from utils import (
    state, AppState, get_app_state, clean_text, count_records, load_data_db,
    save_data_batch, encode_text_batch, save_faiss_index, save_cache,
    initialize_cache_and_index, init_db_pool, close_db_state, init_db,
    CACHE_PATH, FAISS_INDEX_PATH, FINE_TUNE_THRESHOLD, FINE_TUNE_INTERVAL
)
from sentence_transformers import SentenceTransformer

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

# Khởi tạo FastAPI
app = FastAPI()

# Cấu hình CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# API tải lên file Excel
@app.post("/upload-excel")
async def upload_excel(file: UploadFile = File(...), state: AppState = Depends(get_app_state)):
    if not file.filename.endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Only Excel files (.xls, .xlsx) supported")
    try:
        if state.db_pool is None:
            logger.error("Database pool is not initialized")
            raise HTTPException(status_code=500, detail="Database connection not initialized")
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents), engine='openpyxl')
        if 'question' not in df.columns or 'answer' not in df.columns:
            raise HTTPException(status_code=400, detail="Excel must have 'question' and 'answer' columns")
        if len(df) > 10000:
            raise HTTPException(status_code=400, detail="Exceed 10,000 records")

        # Kiểm tra và chuyển đổi kiểu dữ liệu trước khi gọi .str methods
        for col in ['question', 'answer']:
            if df[col].isnull().any() or not pd.api.types.is_string_dtype(df[col]):
                df[col] = df[col].fillna('').astype(str)  # Điền null bằng chuỗi rỗng và chuyển thành chuỗi
            df[col] = df[col].str.strip() #loai bỏ khoảng trắng thừa
            if df[col].str.len().eq(0).any():
                raise HTTPException(status_code=400, detail="Questions and answers cannot be empty")

        records = []
        new_embeddings = []
        skipped_empty = 0
        skipped_duplicate = 0
        async with state.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for _, row in df.iterrows(): #lặp qua từng hàng
                    q = row['question']
                    a = row['answer']
                    q_clean = clean_text(q)
                    a_clean = clean_text(a)
                    if not q_clean or not a_clean:
                        logger.info(f"Skipped empty question-answer pair after cleaning: question='{q}', answer='{a}'")
                        skipped_empty += 1
                        continue
                    await cursor.execute(
                        "SELECT id FROM qa_data WHERE question = %s AND answer = %s LIMIT 1",
                        (q, a)
                    )
                    if await cursor.fetchone():
                        logger.info(f"Skipped duplicate question-answer pair: {q}")
                        skipped_duplicate += 1
                        continue
                    emb = encode_text_batch([q_clean], state)[0]
                    records.append((datetime.now(), q, a, emb.tobytes()))
                    new_embeddings.append((emb, q, a, q_clean, a_clean))
        if not records:
            logger.error(f"No valid records to save: {skipped_empty} empty after cleaning, {skipped_duplicate} duplicates")
            raise HTTPException(
                status_code=401,
                detail=f"No valid records to save: {skipped_empty} empty after cleaning, {skipped_duplicate} duplicates"
            )
        inserted_data = await save_data_batch(records, state) # trả về danh sách (id, question, answer)
        inserted_ids = [data[0] for data in inserted_data]
        new_questions = [data[1] for data in new_embeddings]
        new_answers = [data[2] for data in new_embeddings]
        new_clean_questions = [data[3] for data in new_embeddings]
        new_clean_answers = [data[4] for data in new_embeddings]
        new_embs = [data[0] for data in new_embeddings]
        if state.cache_data['embeddings'].size:
            state.cache_data['embeddings'] = np.vstack([state.cache_data['embeddings'], new_embs]) # Gộp với dữ liệu cũ bằng np.vstack hoặc tạo mới.
        else:
            state.cache_data['embeddings'] = np.array(new_embs)
        state.cache_data['ids'].extend(inserted_ids)
        state.cache_data['questions'].extend(new_questions)
        state.cache_data['answers'].extend(new_answers)
        state.cache_data['clean_questions'] = state.cache_data.get('clean_questions', []) + new_clean_questions
        state.cache_data['clean_answers'] = state.cache_data.get('clean_answers', []) + new_clean_answers
        state.cache_data['last_updated'] = datetime.now()
        save_cache(state.cache_data, CACHE_PATH, state.redis_client)
        state.index.add_with_ids(
            np.array(new_embs).astype(np.float32),
            np.array(inserted_ids, dtype=np.int64)
        )
        save_faiss_index(state.index, FAISS_INDEX_PATH, state.redis_client)
        total_records = await count_records(state)
        new_records = total_records - state.last_fine_tune_record_count
        fine_tuned = False
        state.raw_data = await load_data_db(state)
        if new_records >= FINE_TUNE_THRESHOLD and time.time() - state.last_fine_tune > FINE_TUNE_INTERVAL and len(state.raw_data) >= 10:
            try:
                from tasks import fine_tune_task
                logger.info(f"New records ({new_records}) >= {FINE_TUNE_THRESHOLD}, triggering fine-tuning")
                fine_tune_task.delay()
                fine_tuned = True
                state.last_fine_tune = time.time()
                state.last_fine_tune_record_count = total_records
            except ImportError as e:
                logger.error(f"Failed to import fine_tune_task: {e}")
        logger.info(f"Uploaded {len(df)} records, saved {len(inserted_ids)} new records, skipped {skipped_duplicate} duplicates")
        return {
            "message": f"Uploaded {len(df)} records, saved {len(inserted_ids)} new records, skipped {skipped_duplicate} duplicates",
            "fine_tuned": fine_tuned,
            "total_records": total_records,
            "new_records": new_records
        }
    except pd_errors.ParserError:
        logger.error("Invalid Excel file")
        raise HTTPException(status_code=400, detail="Invalid Excel file")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=402, detail="Đã xảy ra lỗi không mong muốn, vui lòng thử lại sau")

# Hàm tìm kiếm với ngưỡng tương đồng
def search_answer(query: str, k: int = 5, state: AppState = Depends(get_app_state), max_distance_threshold: float = 1.0) -> List[Dict]:
    if not query.strip(): # Kiểm tra chuỗi query sau khi loại bỏ khoảng trắng Nếu rỗng...
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    query_clean = clean_text(query)
    query_embedding = encode_text_batch([query_clean], state)[0]
    distances, indices = state.index.search(query_embedding.reshape(1, -1).astype(np.float32), k * 4)

    # Lọc các kết quả dựa trên ngưỡng khoảng cách
    valid_results = []
    id_to_idx = {id_: idx for idx, id_ in enumerate(state.cache_data['ids'])} # Tạo từ điển ánh xạ ID sang chỉ số trong cache.
    for j, i in enumerate(indices[0]): #lặp qua ds ID từ cache
        if i in id_to_idx and distances[0][j] <= max_distance_threshold:
            idx = id_to_idx[i]      # lấy thông tin từ cache thm vào thêm vào valid result
            answer = state.cache_data['answers'][idx]
            question = state.cache_data['questions'][idx]
            clean_answer = state.cache_data['clean_answers'][idx]
            distance = float(distances[0][j])
            valid_results.append({
                "question": question,
                "answer": answer,
                "distance": distance,
                "clean_answer": clean_answer
            })

    if not valid_results:
        logger.warning(f"No results found within threshold {max_distance_threshold} for query: {query_clean}")
        return [{
            "question": "Không tìm thấy câu trả lời phù hợp",
            "answer": "Vui lòng thử lại với câu hỏi khác hoặc kiểm tra dữ liệu.",
            "distance": None
        }]

    # Nhóm theo clean_answer và chọn câu hỏi tốt nhất
    answer_groups = {}
    for result in valid_results:
        clean_answer = result["clean_answer"]
        if clean_answer not in answer_groups:
            answer_groups[clean_answer] = {"questions": [], "min_distance": float('inf')}
        answer_groups[clean_answer]["questions"].append({"question": result["question"], "distance": result["distance"]})
        answer_groups[clean_answer]["min_distance"] = min(answer_groups[clean_answer]["min_distance"], result["distance"])

    # Sắp xếp nhóm theo khoảng cách nhỏ nhất
    sorted_groups = sorted(answer_groups.items(), key=lambda x: x[1]["min_distance"])
    results = []
    used_clean_answers = set()

    # lấy ch s nhỏ nhâ trong nhom
    if sorted_groups:
        top_clean_answer, top_group = sorted_groups[0]
        top_question = min(top_group["questions"], key=lambda x: x["distance"])
        idx = state.cache_data['clean_answers'].index(top_clean_answer)
        top_answer = state.cache_data['answers'][idx]
        results.append({
            "question": top_question["question"],
            "answer": top_answer,
            "distance": top_question["distance"]
        })
        used_clean_answers.add(top_clean_answer)

    for clean_answer, group in sorted_groups[1:]:
        if clean_answer not in used_clean_answers and len(results) < k:
            best_question = min(group["questions"], key=lambda x: x["distance"])
            idx = state.cache_data['clean_answers'].index(clean_answer)
            answer = state.cache_data['answers'][idx]
            results.append({
                "question": best_question["question"],
                "answer": answer,
                "distance": best_question["distance"]
            })
            used_clean_answers.add(clean_answer)

    if len(results) < k:
        logger.warning(f"Only found {len(results)} unique answers within threshold for query: {query_clean}")
    return results[:k]

# API tìm kiếm
class Query(BaseModel):
    question: str
    max_distance_threshold: float = 1.0

@app.post("/search")
async def search(query: Query, state: AppState = Depends(get_app_state)):
    try:
        results = search_answer(query.question, k=5, state=state, max_distance_threshold=query.max_distance_threshold)
        logger.info(f"Search query: {query.question}, found {len(results)} results")
        return results
    except HTTPException as e:
        logger.error(f"Search error: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Lỗi tìm kiếm, vui lòng thử lại sau")

# API cập nhật dữ liệu
class UpdateData(BaseModel):
    question: str
    answer: str

@app.post("/update")
async def update(data_input: UpdateData, state: AppState = Depends(get_app_state)):
    try:
        if state.db_pool is None:
            logger.error("Database pool is not initialized")
            raise HTTPException(status_code=500, detail="Database connection not initialized")
        question = data_input.question
        answer = data_input.answer
        question_clean = clean_text(question)
        answer_clean = clean_text(answer)
        if not question_clean or not answer_clean:
            raise HTTPException(status_code=400, detail="Question and answer cannot be empty")
        async with state.db_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT id FROM qa_data WHERE question = %s AND answer = %s LIMIT 1",
                    (question, answer)
                )
                if await cursor.fetchone():
                    logger.info(f"Skipped duplicate question-answer pair: {question}")
                    return {"message": False}
        new_embedding = encode_text_batch([question_clean], state)[0]
        new_id, q_saved, a_saved = (await save_data_batch(
            [(datetime.now(), question, answer, new_embedding.tobytes())], state
        ))[0]
        state.index.add_with_ids(
            new_embedding.reshape(1, -1).astype(np.float32),
            np.array([new_id], dtype=np.int64)
        )
        if state.cache_data['embeddings'].size:
            state.cache_data['embeddings'] = np.vstack([state.cache_data['embeddings'], new_embedding])
        else:
            state.cache_data['embeddings'] = new_embedding.reshape(1, -1)
        state.cache_data['ids'].append(new_id)
        state.cache_data['questions'].append(question)
        state.cache_data['answers'].append(answer)
        state.cache_data['clean_questions'] = state.cache_data.get('clean_questions', []) + [question_clean]
        state.cache_data['clean_answers'] = state.cache_data.get('clean_answers', []) + [answer_clean]
        state.cache_data['last_updated'] = datetime.now()
        save_cache(state.cache_data, CACHE_PATH, state.redis_client)
        save_faiss_index(state.index, FAISS_INDEX_PATH, state.redis_client)
        logger.info(f"Updated data with ID: {new_id}")
        return {"message": True}
    except Exception as e:
        logger.error(f"Update error: {e}")
        raise HTTPException(status_code=500, detail=f"Update error: {str(e)}")

# API fine-tune thủ công
@app.post("/fine-tune")
async def fine_tune(state: AppState = Depends(get_app_state)):
    try:
        from tasks import fine_tune_task
        fine_tune_task.delay()
        fine_tuned = True
        # state.last_fine_tune = time.time()
        # total_records = await count_records(state)
        # state.last_fine_tune_record_count = total_records
        return {"message": "Fine-tuning scheduled"}
    except Exception as e:
        logger.error(f"Fine-tune API error: {e}")
        raise HTTPException(status_code=500, detail=f"Fine-tune error: {str(e)}")

# API kiểm tra auto fine-tune
# @app.get("/test-auto-fine-tune")
# async def test_auto_fine_tune():
#     await auto_fine_tune()
#     return {"message": "Auto fine-tune triggered"}

# Tự động fine-tune mỗi tuần
async def auto_fine_tune():
    logger.info("Starting auto fine-tune")
    state = get_app_state()
    if not state.auto_fine_tune_enabled:
        logger.info("Auto fine-tune is disabled, skipping")
        return
    try:
        state.raw_data = await load_data_db(state)
        total_records = await count_records(state)
        new_records = total_records - state.last_fine_tune_record_count
        if new_records >= FINE_TUNE_THRESHOLD and len(state.raw_data) >= 10:
            from tasks import fine_tune_task
            logger.info(f"New records ({new_records}) >= {FINE_TUNE_THRESHOLD}, scheduling fine-tune")
            fine_tune_task.delay()
            logger.info("Auto fine-tune scheduled")
        else:
            logger.warning(f"Not enough new records ({new_records}) or total records ({len(state.raw_data)})")
    except Exception as e:
        logger.error(f"Auto fine-tune error: {e}")

# API bật lập lịch
@app.post("/enable-auto-fine-tune")
async def enable_auto_fine_tune(state: AppState = Depends(get_app_state)):
    try:
        if not state.auto_fine_tune_enabled:
            state.auto_fine_tune_enabled = True
            if not scheduler.running:
                scheduler.add_job(auto_fine_tune, 'interval', weeks=1)
                scheduler.start()
                logger.info("Auto fine-tune scheduler enabled and started")
            else:
                logger.info("Auto fine-tune scheduler already running")
        return {"message": "Auto fine-tune scheduling enabled", "status": state.auto_fine_tune_enabled}
    except Exception as e:
        logger.error(f"Error enabling auto fine-tune: {e}")
        raise HTTPException(status_code=500, detail=f"Error enabling auto fine-tune: {str(e)}")

# API tắt lập lịch
@app.post("/disable-auto-fine-tune")
async def disable_auto_fine_tune(state: AppState = Depends(get_app_state)):
    try:
        if state.auto_fine_tune_enabled:
            state.auto_fine_tune_enabled = False
            if scheduler.running:
                scheduler.shutdown()
                logger.info("Auto fine-tune scheduler disabled and shut down")
            else:
                logger.info("Auto fine-tune scheduler already stopped")
        return {"message": "Auto fine-tune scheduling disabled", "status": state.auto_fine_tune_enabled}
    except Exception as e:
        logger.error(f"Error disabling auto fine-tune: {e}")
        raise HTTPException(status_code=500, detail=f"Error disabling auto fine-tune: {str(e)}")

# API kiểm tra trạng thái lập lịch
@app.get("/get-auto-fine-tune-status")
async def get_auto_fine_tune_status(state: AppState = Depends(get_app_state)):
    return {"status": state.auto_fine_tune_enabled, "message": "Auto fine-tune status retrieved"}

# Tắt scheduler
atexit.register(lambda: scheduler.shutdown() if scheduler.running else None)  # Chỉ giữ một lần

# Khởi tạo ứng dụng
@app.on_event("startup")
async def startup_event():
    try:
        logger.debug("Starting application initialization")
        await init_db_pool(state)
        logger.debug("init_db_pool completed")
        await init_db(state)
        logger.debug("init_db completed")
        model_path = os.getenv("MODEL_PATH", "/app/data/phobert_base")
        if not os.path.exists(model_path):
            logger.info("Downloading PhoBERT model from Hugging Face...")
            state.model = SentenceTransformer("vinai/phobert-base")
            os.makedirs(model_path, exist_ok=True)
            state.model.save(model_path)
            logger.info(f"PhoBERT model saved to {model_path}")
        else:
            logger.info(f"Loading PhoBERT model from {model_path}")
            state.model = SentenceTransformer(model_path)
        logger.debug("Model loaded successfully")
        await initialize_cache_and_index(state)
        logger.debug("initialize_cache_and_index completed")

        # Khởi tạo và khởi động scheduler trong startup_event
        global scheduler  # Đảm bảo scheduler là biến toàn cục
        scheduler = AsyncIOScheduler()
        if state.auto_fine_tune_enabled:
            scheduler.add_job(auto_fine_tune, 'interval', weeks=1)
            scheduler.start()
            logger.info("Auto fine-tune scheduler started")
        else:
            logger.info("Auto fine-tune scheduler not started due to disabled state")

        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.critical(f"Startup failed: {e}")
        raise SystemExit(f"Failed to initialize resources: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    await close_db_state(state)