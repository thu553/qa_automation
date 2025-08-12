from transformers import AutoTokenizer, AutoModel
import os

base_path = "./phobert_base"
if not os.path.exists(base_path):
    os.makedirs(base_path)
tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base", trust_remote_code=True)
model = AutoModel.from_pretrained("vinai/phobert-base")
tokenizer.save_pretrained(base_path)
model.save_pretrained(base_path)
print(f"Model and tokenizer saved to {base_path}")