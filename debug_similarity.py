
import cohere
from config.settings import settings
import sys

# Mocking the text chunk from the book
chunk_text = """
The Chicken and Egg Problem: In a Two-
Sided Market, Which Comes First? 
if youre doing customer development with multiple stakehold-
ers, should you talk to one target customer segment first, then the 
other? Or should you alternate?
LaunchBit, a startup that serves a two-sided market, validated its 
ideas through customer development. The company, an ad net-
work for email, needed to understand the needs of both online 
marketers and content publishers.
CEO Elizabeth Yin explains, its hard to tackle a two-sided market. 
People say get one side first, then use that to get to the other side, 
but that approach wasnt really possible for us. ...
LaunchBit was able to identify painful problems for each side. 
Marketers didnt want to have to do one-off business develop-
ment deals to advertise in newsletters. LaunchBit would give the 
marketers the ability to target multiple newsletters with one buy, 
and that won their business. Content publishers didnt want to run 
banner ads, even if they made money, because of concern theyd 
alienate readers. LaunchBit switched its ad format to text ads to 
keep publishers happyand without publishers, theyd have no 
product for marketers.
"""

queries = [
    "i am thinking of an idea. it helps bridge gap between kirana stores and d2c brands. i have validated by talking to d2c brands that it is problem for them and logically i think it makes sense for kirana stores too. should i go ahead with the product?",
    "LaunchBit two sided market validation",
    "how to validate two sided market",
    "LaunchBit example"
]

try:
    co = cohere.Client(settings.COHERE_API_KEY)
    
    # Embed the chunk
    response_doc = co.embed(
        texts=[chunk_text],
        model="embed-english-v3.0",
        input_type="search_document"
    )
    doc_embedding = response_doc.embeddings[0]
    
    # Embed queries
    response_query = co.embed(
        texts=queries,
        model="embed-english-v3.0",
        input_type="search_query"
    )
    query_embeddings = response_query.embeddings
    
    # Calculate cosine similarity manually
    def cosine_similarity(v1, v2):
        dot_product = sum(a*b for a,b in zip(v1, v2))
        norm_v1 = sum(a*a for a in v1) ** 0.5
        norm_v2 = sum(b*b for b in v2) ** 0.5
        return dot_product / (norm_v1 * norm_v2)

    print(f"Similarity Threshold in Settings: {settings.SIMILARITY_THRESHOLD}")
    print("-" * 50)
    
    for i, query in enumerate(queries):
        score = cosine_similarity(query_embeddings[i], doc_embedding)
        print(f"Query: {query[:50]}...")
        print(f"Similarity Score: {score:.4f}")
        print("-" * 50)

except Exception as e:
    print(f"Error: {e}")
