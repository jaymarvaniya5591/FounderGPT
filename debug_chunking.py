
import re
from config.settings import settings

def semantic_chunk_text(text, chunk_size, chunk_overlap):
    chunks = []
    # Split into sentences (approximate)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        sentence_length = len(sentence.split())
        
        if current_length + sentence_length > chunk_size:
            if current_chunk:
                chunk_text = ' '.join(current_chunk)
                if len(chunk_text.strip()) > 50:
                    chunks.append(chunk_text)
                
                # Keep overlap
                overlap_words = chunk_overlap
                overlap_sentences = []
                overlap_count = 0
                for s in reversed(current_chunk):
                    s_words = len(s.split())
                    if overlap_count + s_words <= overlap_words:
                        overlap_sentences.insert(0, s)
                        overlap_count += s_words
                    else:
                        break
                
                current_chunk = overlap_sentences
                current_length = overlap_count
        
        current_chunk.append(sentence)
        current_length += sentence_length
    
    # Don't forget the last chunk
    if current_chunk:
        chunk_text = ' '.join(current_chunk)
        if len(chunk_text.strip()) > 50:
            chunks.append(chunk_text)
    
    return chunks

# Text from the previous step
text = """
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
but that approach wasnt really possible for us. 
We first started out rounding up six publishers and two adver-
tisers, said Yin. The two advertisers were willing to test new ad 
inventory, so they were willing to use our MVP of minimal ad cam-
paigns. The six publishers likewise were interested in testing the 
idea of monetizing their newsletters. So, in the beginning we had 
small numbers of participants from both sides using MVPs. We 
structured everything as an experiment. This worked for people 
who enjoy experimenting with new ideas. Once those early ex-
periments went well, we were able to expand both groups. We 
started to get some scale, and that made our numbers look more 
interesting to potential customers who were less comfortable with 
experiments.
its hard to predict who you should ideally interview first, so dont 
get too caught up in worrying about it. Jump in and start inter-
viewing. Youll probably have a good sense after a couple of inter-
views about how it is most possible and practical to hear from all 
the stakeholders you are serving.
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

# Test with current and potentially new settings
configs = [
    {"size": 700, "overlap": 140},
    {"size": 500, "overlap": 50},
    {"size": 1000, "overlap": 200}
]

print(f"Total words in text: {len(text.split())}")

for config in configs:
    print(f"\n--- Testing Config: Size {config['size']}, Overlap {config['overlap']} ---")
    chunks = semantic_chunk_text(text, config['size'], config['overlap'])
    for i, chunk in enumerate(chunks):
        words = len(chunk.split())
        has_key_phrase = "LaunchBit was able to identify" in chunk
        print(f"Chunk {i+1} ({words} words): Contains target? {has_key_phrase}")
        if has_key_phrase:
            print(f"  > {chunk[:100]}...")
