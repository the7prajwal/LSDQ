"""
Location-aware chunker for RAG.
"""


def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list:
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = end - overlap
    return chunks


def chunk_segments(segments: list, chunk_size: int = 300, overlap: int = 50) -> list:
    results = []
    for seg in segments:
        text = seg["text"]
        location = seg["location"]
        word_count = len(text.split())

        if word_count <= chunk_size:
            results.append({"text": text, "location": location})
        else:
            sub_chunks = chunk_text(text, chunk_size, overlap)
            for i, sub in enumerate(sub_chunks, start=1):
                results.append({
                    "text": sub,
                    "location": f"{location} (part {i})",
                })

    return results
