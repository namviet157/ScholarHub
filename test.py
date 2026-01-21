# from pymongo import MongoClient
# from dotenv import load_dotenv
# import os
# from supabase import create_client, Client
# from processing.embeddings import get_embedding_service
# from processing.summarization import get_summarizer

# load_dotenv()

# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# if not SUPABASE_URL or not SUPABASE_KEY:
#     raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# MONGO_URL = os.getenv("MONGO_URL")
# DATABASE_NAME = os.getenv("DATABASE_NAME")
# COLLECTION_NAME = os.getenv("DOCUMENT_CONTENTS_COLLECTION")

# if not MONGO_URL or not DATABASE_NAME or not COLLECTION_NAME:
#     raise ValueError("MONGO_URL, DATABASE_NAME, and DOCUMENT_CONTENTS_COLLECTION must be set in .env file")

# client = MongoClient(MONGO_URL)
# db = client[DATABASE_NAME]
# collection = db[COLLECTION_NAME]

# data = collection.find_one({"paper_id": "2304-14608"})
# summaries = data.get("summaries")
# document_summary = summaries.get("document_summary")
# abstract_summary = summaries.get("abstract_summary")
# print(document_summary)
# print("-" * 100)
# print(abstract_summary)
# print("-" * 100)
# print(document_summary == abstract_summary)

from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F

#Mean Pooling - Take attention mask into account for correct averaging
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0] #First element of model_output contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


# Sentences we want sentence embeddings for
sentences = ['This is an example sentence', 'Each sentence is converted']

# Load model from HuggingFace Hub
tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
model = AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')

# Tokenize sentences
encoded_input = tokenizer(sentences, padding=True, truncation=True, return_tensors='pt')

# Compute token embeddings
with torch.no_grad():
    model_output = model(**encoded_input)

# Perform pooling
sentence_embeddings = mean_pooling(model_output, encoded_input['attention_mask'])

# Normalize embeddings
sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)

print("Sentence embeddings:")
print(sentence_embeddings)
