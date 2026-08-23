import os
from typing import Optional, List
from dotenv import load_dotenv
from fastapi import HTTPException
from groq import Groq

from app.vector_db import search_document_chunks
from app.schemas import Citation, ChatResponse

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

SYSTEM_PROMPT = """You are SmartDocs AI, an expert, in-depth document analysis assistant.

Your task is to provide comprehensive, detailed, and insightful answers to the user's questions using the provided document context chunks below.

Rules:
1. Ground your answer thoroughly in the provided context.
2. Explain concepts deeply and clearly with structure, elaboration, and relevant examples from the text.
3. If the context does not contain enough information to answer the question, state clearly: "I cannot find sufficient information in the provided documents to answer that."
4. Do not invent facts or extrapolate beyond what the context supports.
5. Provide in-depth explanations covering all parts of the user's question, using bullet points and headings where appropriate.
6. Reference sources (e.g., [Source 1], [Source 2]) to support key points.
"""


def get_active_model(client: Groq) -> str:
    """Selects the best available general conversation chat model on Groq."""
    try:
        models_data = client.models.list().data
        available_ids = [m.id for m in models_data]

        chat_models = [
            m for m in available_ids
            if not any(bad in m.lower() for bad in ["guard", "safety", "safeguard", "whisper", "vision", "embed"])
        ]

        priority_list = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "openai/gpt-oss-120b",
            "llama3-8b-8192",
            "llama3-70b-8192",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ]

        for preferred in priority_list:
            if preferred in chat_models:
                return preferred

        return chat_models[0] if chat_models else "llama3-8b-8192"
    except Exception:
        return "llama3-8b-8192"


def decompose_query(question: str, client: Groq, model: str) -> List[str]:
    """Breaks complex, multi-part questions into 1-3 distinct search sub-queries."""
    try:
        decomposition_prompt = f"""Break down the following user question into 1 to 3 distinct, concise search queries for retrieving relevant paragraphs from a vector database.
Output ONLY the search queries, one per line. Do not number them.

Question: {question}"""

        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": decomposition_prompt}],
            temperature=0.0,
            max_tokens=150,
        )
        lines = completion.choices[0].message.content.strip().split("\n")
        queries = [q.strip("- *0123456789. ") for q in lines if q.strip()]
        return queries if queries else [question]
    except Exception:
        return [question]


def generate_rag_answer(
    question: str,
    owner_id: str,
    document_id: Optional[str] = None,
    top_k: int = 6,
    min_score: float = 0.20,
) -> ChatResponse:
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY is missing from .env. Please add it and restart uvicorn.",
        )

    client = Groq(api_key=GROQ_API_KEY)
    model_to_use = get_active_model(client)

    # 1. Multi-Query Decomposition: Break complex questions into sub-queries
    sub_queries = decompose_query(question, client, model_to_use)
    if question not in sub_queries:
        sub_queries.append(question)

    # 2. Retrieve chunks for all sub-queries and deduplicate
    seen_chunk_keys = set()
    all_matching_chunks = []

    for query_text in sub_queries:
        chunks = search_document_chunks(
            query=query_text,
            owner_id=owner_id,
            document_id=document_id,
            limit=top_k,
            min_score=min_score,
        )
        for chunk in chunks:
            chunk_key = (chunk.get("document_id"), chunk.get("chunk_index"))
            if chunk_key not in seen_chunk_keys:
                seen_chunk_keys.add(chunk_key)
                all_matching_chunks.append(chunk)

    # Sort all retrieved chunks by highest relevance score and keep top_k * 2
    all_matching_chunks.sort(key=lambda x: x.get("score", 0), reverse=True)
    all_matching_chunks = all_matching_chunks[: max(top_k, 8)]

    # 3. Build Citations & Context Blocks
    citations: List[Citation] = []
    context_blocks: List[str] = []

    for idx, chunk in enumerate(all_matching_chunks, start=1):
        citations.append(
            Citation(
                document_id=chunk["document_id"],
                filename=chunk["filename"],
                chunk_index=chunk["chunk_index"],
                score=chunk["score"],
                snippet=chunk["text"][:250] + "..." if len(chunk["text"]) > 250 else chunk["text"],
            )
        )
        context_blocks.append(
            f"[Source {idx}] (File: {chunk['filename']}, Chunk #{chunk['chunk_index']}):\n{chunk['text']}"
        )

    # 4. Assemble Prompt
    if not all_matching_chunks:
        context_text = "No relevant document chunks found in the user's uploaded files."
    else:
        context_text = "\n\n---\n\n".join(context_blocks)

    user_prompt = f"""DOCUMENT CONTEXT:
{context_text}

---

USER QUESTION:
{question}

IN-DEPTH ANSWER:"""

    # 5. Call Groq Cloud LLM for in-depth answer
    try:
        chat_completion = client.chat.completions.create(
            model=model_to_use,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        generated_answer = chat_completion.choices[0].message.content or ""
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Groq LLM Generation Error: {str(e)}",
        )

    return ChatResponse(
        question=question,
        answer=generated_answer.strip(),
        citations=citations,
        model_used=model_to_use,
    )