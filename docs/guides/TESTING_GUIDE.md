# Testing Guide for PDF Retrieval

## Purpose
This guide helps you test and debug the PDF retrieval functionality to ensure information from PDF manuals is being retrieved and displayed correctly.

## Prerequisites
1. **Milvus is running**: `docker-compose ps` should show all services healthy
2. **Neo4j is running**: Check connection in app
3. **Data is loaded**: Both Neo4j and Milvus should have data

## Testing Steps

### 1. Check Milvus Data
```bash
cd "/Users/suayshkulashri/Desktop/CSV RAG"
python database/test_milvus_connection.py
```

**Expected output:**
```
✓ Connected to Milvus at localhost:19531
✓ Collection 'partstown_pdfs' already exists
✅ Milvus connection successful!
   Collection: partstown_pdfs
   Entities: 395
```

If you see "Entities: 0", you need to re-ingest the CSV with PDF processing enabled.

### 2. Start the Application
```bash
streamlit run app.py
```

### 3. Monitor Debug Output
The application now prints detailed debug information to the terminal where you ran `streamlit run app.py`. Look for:

```
============================================================
USER QUERY: Tell me about part TRNXXXXXXX
============================================================

Parsed Query:
  Intent: part_info
  Parts: ['TRNXXXXXXX']
  Models: []

🔍 Milvus Retrieval:
  Query: Tell me about part TRNXXXXXXX
  Parts queried: ['TRNXXXXXXX']
  Parts with PDFs in Neo4j: ['TRNXXXXXXX']
  Generating embeddings...
  Filter expression: parts_town_number == 'TRNXXXXXXX'
  Searching Milvus for top 10 results...
  Raw search results: 5 chunks returned
  ✓ Found 3 relevant chunks (max distance: 1.5)
    Best match distance: 0.1234
    Worst match distance: 0.8765
    [1] Part: TRNXXXXXXX, Page: 12, Distance: 0.1234
    [2] Part: TRNXXXXXXX, Page: 15, Distance: 0.5678
    [3] Part: TRNXXXXXXX, Page: 18, Distance: 0.8765

📝 Building Response:
  Neo4j results: 1 parts, 0 models
  Milvus results: 3 PDF chunks
  Extracted 1 unique PDF URLs
    [1] https://example.com/manual.pdf...

Response built:
  PDF URLs to display: 1
============================================================
```

### 4. Test Cases

#### Test Case 1: Part with PDF
**Query:** "Tell me about part [PART_NUMBER]"

**What to check:**
- ✅ "Parts with PDFs in Neo4j" shows the part
- ✅ "Milvus results" > 0 chunks
- ✅ PDF URL appears in response
- ✅ Page numbers are cited in the response
- ✅ PDF URL appears at the bottom of the chat message

#### Test Case 2: Part without PDF
**Query:** "Tell me about part [PART_NUMBER_WITHOUT_PDF]"

**What to check:**
- ✅ "Parts with PDFs in Neo4j" is empty []
- ✅ "Milvus results" = 0 chunks
- ✅ Response says "PDF manual not available for this part"
- ✅ No PDF URLs displayed

#### Test Case 3: Model Information
**Query:** "Tell me about model [MODEL_NAME]"

**What to check:**
- ✅ Lists parts (first 5 or all if ≤7)
- ✅ Shows "and X more" if total > 7
- ✅ If parts have PDFs, Milvus results > 0
- ✅ PDF information included if available

#### Test Case 4: Installation Instructions
**Query:** "How do I install part [PART_NUMBER]"

**What to check:**
- ✅ Milvus retrieves relevant installation chunks
- ✅ Response includes: "According to the manual (Page X): ..."
- ✅ PDF URL and page numbers are cited
- ✅ Installation steps from PDF are included

## Troubleshooting

### Issue: "Milvus results: 0 chunks" even though part has PDF

**Possible causes:**
1. **Similarity threshold too strict**: Current max distance is 1.5. Check debug output for "Raw search results".
2. **Embedding mismatch**: Query embedding might not match PDF chunk embeddings.
3. **Filter expression issue**: Check if the filter is too restrictive.

**Solutions:**
- Increase `max_distance` in `query_engine/retriever.py` (line 342) from 1.5 to 2.0
- Try a more specific query (e.g., "installation instructions" instead of "tell me about")
- Check if the part number in Neo4j matches exactly with Milvus

### Issue: "Parts with PDFs in Neo4j: []" but you know the part has a PDF

**Possible causes:**
1. **Part number mismatch**: Neo4j part name vs CSV "Parts Town #"
2. **PDF relationship not created**: Check if HAS_MANUAL relationship exists

**Solutions:**
```bash
# Check Neo4j relationships
python database/diagnose_neo4j.py
```

Look for:
- Part nodes with correct names
- PDF nodes with URLs
- HAS_MANUAL relationships

### Issue: PDF URL appears but no content from PDF

**Possible causes:**
1. **Filter too restrictive**: Part number doesn't match exactly
2. **Distance threshold too strict**: No chunks pass the similarity filter

**Solutions:**
- Check debug output for "Raw search results" count
- If > 0, increase max_distance threshold
- If = 0, there might be a filter expression issue

### Issue: Application shows PDF info when it shouldn't

**Possible causes:**
1. **Fallback search triggered**: Broader search found unrelated PDFs

**Solutions:**
- Check if the broader search is being triggered
- Adjust the logic in retriever to be more conservative

## Expected Behavior Summary

### When PDF is Available:
1. ✅ "PDF Manuals Available: YES" in context
2. ✅ PDF URLs listed in part information
3. ✅ Milvus returns relevant chunks
4. ✅ Response includes: "According to the [manual](PDF_URL) on page X: ..."
5. ✅ PDF URLs displayed at bottom of response

### When PDF is NOT Available:
1. ✅ "PDF Manuals Available: NO" in context
2. ✅ No Milvus search performed (or returns 0)
3. ✅ Response says: "PDF manual not available for this part"
4. ✅ No PDF URLs displayed
5. ✅ No fabricated PDF information

## Performance Tuning

### If retrieving too few results:
- Increase `max_distance` in `retriever.py` (line 342)
- Increase `top_k` parameter (default is 5)
- Lower similarity threshold (but may reduce quality)

### If retrieving irrelevant results:
- Decrease `max_distance` (make it stricter)
- Improve query parsing to be more specific
- Use more specific part number filters

## Sample Test Queries

```
1. "Tell me about part TRNBRG00104"
2. "How do I install TRNBRG00104?"
3. "What are the specifications for TRNBRG00104?"
4. "Tell me about model TAH066C100A0"
5. "What parts are in model TAH066C100A0?"
6. "Installation instructions for TAH066C100A0"
```

Check terminal output for each query to see the debug information.


