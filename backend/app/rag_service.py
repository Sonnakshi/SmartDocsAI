import os
import re
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from fastapi import HTTPException
from groq import Groq

from app.vector_db import search_document_chunks
from app.schemas import Citation, ChatResponse

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

SYSTEM_PROMPT = """You are SmartDocs AI, an expert, in-depth document analysis assistant with conversational memory.

Your task is to provide comprehensive, detailed, and insightful answers to the user's questions using the provided document context chunks and recent conversation history.

Rules:
1. Ground your answers thoroughly in the provided document context and prior conversational context.
2. If the user asks for summaries, shortening, reformatting, or follow-up explanations on previous answers, use the recent conversation history to fulfill their request while keeping all facts grounded.
3. If the context does not contain enough information to answer a new question, state clearly: "I cannot find sufficient information in the provided documents to answer that."
4. Do not invent facts or extrapolate beyond what the context supports.
5. Provide structured answers with bullet points and headings where appropriate.
6. Reference sources (e.g., [Source 1], [Source 2]) when citing facts from retrieved documents.
7. For mathematical formulas, equations, or scientific notation, ALWAYS use standard dollar signs:
   - Use $formula$ for inline math (e.g. $\ln(x)$, $x^2 + y^2 = r^2$, $\log_{10}(5)$).
   - Use $$formula$$ on its own line for block equations.
   - Do NOT use \\( or \\) notation or <br> tags.
8. If the user asks to "plot a graph", "visualize", "show a chart", or illustrate mathematical equations/distributions visually, generate executable Python code using `matplotlib.pyplot` inside a ```python ``` block. Ensure code sets labels, title, grid, and uses `plt.plot()`. Do not call `plt.show()`.
9. If the user asks to "generate an image", "create a photo", "draw", or "show an illustration" of a scene, character, or concept from the document, provide a descriptive image prompt formatted strictly as: [IMAGE_PROMPT: detailed visual description of the scene or subject].
"""


def format_latex_math(text: str) -> str:
    """Auto-converts any raw LaTeX \( ... \) or \[ ... \] into standard $ ... $ and $$ ... $$."""
    # Convert \[ ... \] to $$ ... $$
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    # Convert \( ... \) to $ ... $
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    # Clean up accidental unrendered <br> tags
    text = text.replace("<br>", "\n")
    return text


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
            "openai/gpt-oss-120b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
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


def contextualize_and_decompose_query(
    question: str,
    chat_history: Optional[List[Dict[str, Any]]],
    client: Groq,
    model: str,
) -> List[str]:
    """Rewrites follow-up questions into standalone search queries using chat history."""
    if not chat_history:
        prompt = f"""Break down the following user question into 1 to 3 distinct, concise search queries for retrieving relevant paragraphs from a vector database.
Output ONLY the search queries, one per line. Do not number them.

Question: {question}"""
    else:
        history_snippet = "\n".join(
            f"{msg.get('role', 'user')}: {msg.get('content', '')[:300]}"
            for msg in chat_history[-4:]
        )
        prompt = f"""Given the following recent conversation history and a follow-up user request, rewrite the request into 1 to 3 standalone search queries that capture the main topic for vector search.
If the request is an instruction like "make this shorter in 200 words" or "summarize that", identify the underlying subject being discussed.

Conversation History:
{history_snippet}

Follow-up Request: {question}

Output ONLY the search queries, one per line. Do not number them:"""

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
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
    chat_history: Optional[List[Dict[str, Any]]] = None,
) -> ChatResponse:
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY is missing from .env. Please add it and restart uvicorn.",
        )

    client = Groq(api_key=GROQ_API_KEY)
    model_to_use = get_active_model(client)

    # 1. Query Contextualization & Multi-Query Search
    sub_queries = contextualize_and_decompose_query(question, chat_history, client, model_to_use)
    if question not in sub_queries:
        sub_queries.append(question)

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

    all_matching_chunks.sort(key=lambda x: x.get("score", 0), reverse=True)
    all_matching_chunks = all_matching_chunks[: max(top_k, 8)]

    # 2. Build Citations & Context Blocks
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

    context_text = "\n\n---\n\n".join(context_blocks) if context_blocks else "No relevant document chunks found."

    # 3. Assemble Multi-Turn Conversation Messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if chat_history:
        for prev_msg in chat_history[-6:]:
            role = prev_msg.get("role", "user")
            content = prev_msg.get("content", "")
            if content.strip():
                messages.append({"role": role, "content": content})

    current_prompt = f"""DOCUMENT CONTEXT:
{context_text}

---

USER REQUEST:
{question}

ANSWER:"""
    messages.append({"role": "user", "content": current_prompt})

    # 4. Generate Answer with Groq LLM
    try:
        chat_completion = client.chat.completions.create(
            model=model_to_use,
            messages=messages,
            temperature=0.2,
            max_tokens=1500,
        )
        raw_answer = chat_completion.choices[0].message.content or ""
        # Auto-format LaTeX for Streamlit rendering
        formatted_answer = format_latex_math(raw_answer)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Groq LLM Generation Error: {str(e)}",
        )

    return ChatResponse(
        question=question,
        answer=formatted_answer.strip(),
        citations=citations,
        model_used=model_to_use,
    )