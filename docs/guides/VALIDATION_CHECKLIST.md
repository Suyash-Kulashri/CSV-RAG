# Validation Checklist - Preventing LLM Hallucination

## ⚠️ Important Reality Check

**While we've implemented strong anti-hallucination measures, LLMs are probabilistic systems and 100% guarantee is impossible.**

This checklist helps you validate outputs and catch any potential hallucinations.

---

## What We've Done to Minimize Hallucination

### 1. ✅ System Prompt Safeguards
- Critical rules at the top of every prompt
- Explicit "NO FABRICATION" instructions
- Examples of correct vs incorrect behavior
- "YOU ARE A TEXT COPIER" framing for PDF queries

### 2. ✅ Temperature Set to 0
- Reduced from 0.7 to 0.0 for maximum determinism
- Minimizes creative/random outputs
- Makes responses more predictable

### 3. ✅ Query-Type-Specific Instructions
- Different rules for part/model/PDF queries
- Explicit handling of missing data
- Verbatim copying requirements for PDF content

### 4. ✅ Multiple Validation Layers
- Context only includes provided data
- Instructions repeated in multiple ways
- Concrete examples of wrong behavior

---

## Testing Protocol

### Test Every Query Type

#### 1. General Part Query
**Test Query:** "Tell me about part [PART_NUMBER]"

**Validation:**
- [ ] All fields match Neo4j database exactly
- [ ] Manufacturer # shows "N/A" if missing (not fabricated)
- [ ] PDF excerpts are summaries, not verbatim (acceptable for general queries)
- [ ] No information added that isn't in the database

**How to Verify:**
```bash
# Check Neo4j for this part
python -c "
from database.neo4j_client import Neo4jClient
client = Neo4jClient()
query = '''
MATCH (p:Part {name: '[PART_NUMBER]'})
RETURN p
'''
result = client.execute_query(query)
print(dict(result[0]['p']))
"
```

---

#### 2. General Model Query
**Test Query:** "Tell me about model [MODEL_NAME]"

**Validation:**
- [ ] Model name matches exactly
- [ ] Parts list matches Neo4j exactly
- [ ] If > 7 parts, shows first 5 + "and X more"
- [ ] If ≤ 7 parts, shows all
- [ ] No parts added that aren't in database

**How to Verify:**
```bash
# Check Neo4j for this model
python -c "
from database.neo4j_client import Neo4jClient
client = Neo4jClient()
query = '''
MATCH (m:Model {name: '[MODEL_NAME]'})-[:HAS_PART]->(p:Part)
RETURN p.\`Parts Town #\` as part
'''
result = client.execute_query(query)
for r in result:
    print(r['part'])
"
```

---

#### 3. PDF Detail Query (CRITICAL)
**Test Query:** "How do I install [PART_NUMBER]?" or "What are the specs for [PART_NUMBER]?"

**Validation:**
- [ ] Text is VERBATIM from manual (compare word-for-word)
- [ ] No bullet points unless in original
- [ ] No added phrases like "involves the following"
- [ ] Page numbers are cited
- [ ] If incomplete info, states so (doesn't fill gaps)

**How to Verify:**
```bash
# Get actual PDF content from Milvus
python -c "
from database.milvus_client import MilvusClient
from utils.embeddings import EmbeddingGenerator

milvus = MilvusClient()
embedding_gen = EmbeddingGenerator()

query = 'installation [PART_NUMBER]'
query_embedding = embedding_gen.generate_embeddings(query)
filter_expr = \"parts_town_number == '[PART_NUMBER]'\"

results = milvus.search(
    query_embedding=query_embedding[0],
    top_k=5,
    filter_expr=filter_expr
)

for i, r in enumerate(results, 1):
    print(f'\\nResult {i} - Page {r.get(\"page_number\")}:')
    print(r.get('text', '')[:500])
"
```

**Manual Verification:**
1. Open the actual PDF from the URL shown
2. Go to the page number cited
3. **Compare text word-for-word** with LLM output
4. Look for ANY additions, deletions, or restructuring

---

#### 4. Missing Information Query
**Test Query:** "What is the weight of [PART_NUMBER]?" (when weight isn't in data)

**Validation:**
- [ ] States "information not available" or similar
- [ ] Does NOT provide a weight value
- [ ] Does NOT say "typically" or "usually"
- [ ] Does NOT provide generic information

---

## Red Flags - Report Immediately

### 🚨 Critical Issues

1. **Fabricated Technical Details**
   - Part numbers that don't exist
   - Specifications not in the manual
   - Steps or procedures not in the PDF

2. **Added Structure**
   - Bullet points created from paragraphs
   - Section headings not in original
   - "The process involves..." or similar transitions

3. **Generic Information**
   - "Typically..." or "Usually..."
   - "Standard HVAC procedures..."
   - Information from "general knowledge"

4. **Assumptions**
   - Filling gaps in incomplete excerpts
   - Inferring missing specifications
   - Adding "obvious" steps not mentioned

---

## Weekly Validation Routine

### Sample 10 Random Queries Per Week

```bash
# Run this test script weekly
python test_hallucination.py
```

**Test Cases to Include:**
1. 2 general part queries (with and without PDF)
2. 2 general model queries (small and large parts list)
3. 3 PDF detail queries (installation, specs, troubleshooting)
2. 2 missing information queries
1. 1 edge case (unusual phrasing)

**For each:**
- [ ] Verify against source data
- [ ] Check for fabrication
- [ ] Document any issues

---

## Monitoring Setup

### Log All Queries and Responses

Add to `app.py`:
```python
import json
from datetime import datetime

# After response is generated
log_entry = {
    'timestamp': datetime.now().isoformat(),
    'query': user_query,
    'intent': parsed_query.get('intent'),
    'parts': parsed_query.get('parts_town_numbers'),
    'models': parsed_query.get('model_names'),
    'response_length': len(response['response']),
    'pdf_urls': response.get('pdf_urls', []),
    'milvus_chunks': len(retrieval_results.get('milvus_results', []))
}

with open('query_log.jsonl', 'a') as f:
    f.write(json.dumps(log_entry) + '\n')
```

**Review logs weekly for:**
- Patterns in queries that might cause issues
- Unusual response lengths (too short or too long)
- Queries with no Milvus chunks but expecting PDF info

---

## User Feedback Loop

### Add Feedback Mechanism

At the end of each response in `app.py`, add:
```python
col1, col2 = st.columns(2)
with col1:
    if st.button("👍 Accurate", key=f"good_{i}"):
        # Log positive feedback
        pass
with col2:
    if st.button("👎 Inaccurate", key=f"bad_{i}"):
        # Log negative feedback + show form
        with st.form(key=f"feedback_{i}"):
            issue = st.text_area("What was wrong?")
            if st.form_submit_button("Submit"):
                # Log the issue for review
                pass
```

**Review negative feedback:**
- Identify patterns
- Update prompts if needed
- Add to test cases

---

## Known Limitations

### What Can Still Go Wrong

1. **Complex Queries**
   - Multi-part questions might confuse the system
   - Ambiguous phrasing could trigger wrong behavior
   
2. **Context Length**
   - Very long PDF excerpts might cause truncation
   - System might "forget" instructions with large context

3. **Rare Query Types**
   - Questions we haven't tested for
   - Unusual technical terminology
   
4. **Temperature Randomness**
   - Even at 0.0, small variations can occur
   - Different runs might produce slightly different wording

---

## When to Escalate

### Contact Developer If:

1. **Fabricated Information Appears**
   - Part numbers that don't exist
   - Specifications not in manual
   - Installation steps not in PDF

2. **Pattern of Issues**
   - Same type of query consistently fails
   - Specific part/model always has issues
   
3. **Safety-Critical Errors**
   - Wrong wiring instructions
   - Incorrect safety procedures
   - Dangerous installation steps

---

## Best Practices for Users

### How to Use the System Safely

1. **Cross-Reference Critical Information**
   - For installation: Check the actual PDF
   - For specifications: Verify with manual
   - For safety procedures: Always consult original documentation

2. **Use Specific Queries**
   - ✅ "How do I install TRNPAN02916?"
   - ❌ "Tell me about installation"

3. **Check Page Numbers**
   - Every PDF-based answer should cite pages
   - Open the PDF and verify the information

4. **Look for Red Flags**
   - Bullet points in detailed queries (usually wrong)
   - Generic language ("typically", "usually")
   - Information that seems too perfect or organized

---

## Emergency Rollback

### If Hallucination Becomes Problematic

**Increase Model Conservativeness:**

In `response_builder.py`, change:
```python
temperature=0.0,
max_tokens=2000,
top_p=0.1,  # Add this - more conservative
```

**Add Stricter Filtering:**

Add a post-processing check:
```python
def validate_response(response, context):
    # Check if response contains text not in context
    # Flag suspicious patterns
    # Return validation result
    pass
```

---

## Summary

### Current Protection Level: **HIGH** 🟢

**Strengths:**
- ✅ Strong prompt engineering
- ✅ Temperature set to 0
- ✅ Multiple validation layers
- ✅ Query-type-specific rules
- ✅ Explicit examples

**Remaining Risks:**
- ⚠️ LLMs are probabilistic (can't be 100%)
- ⚠️ Untested edge cases
- ⚠️ Complex/ambiguous queries
- ⚠️ Rare query types

**Recommendation:**
- Use the system with confidence for typical queries
- Always verify critical/safety information
- Monitor and validate regularly
- Report any issues immediately

---

## Quick Validation Command

```bash
# Test a specific query
python -c "
from query_engine.query_parser import QueryParser
from query_engine.retriever import Retriever
from query_engine.response_builder import ResponseBuilder
from database.neo4j_client import Neo4jClient
from database.milvus_client import MilvusClient
from utils.embeddings import EmbeddingGenerator

# Initialize
neo4j = Neo4jClient()
milvus = MilvusClient()
embedding_gen = EmbeddingGenerator()

parser = QueryParser()
retriever = Retriever(neo4j, milvus, embedding_gen)
builder = ResponseBuilder()

# Test query
query = 'Tell me about part TRNPAN02916'
parsed = parser.parse(query)
results = retriever.retrieve(parsed)
response = builder.build_response(query, results)

print('Intent:', parsed['intent'])
print('\\nResponse:')
print(response['response'][:500])
"
```

---

**Remember: Trust, but verify. The system is good, but not perfect.**

