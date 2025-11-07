"""
Response builder for combining and formatting query results using OpenAI GPT-4.
"""
import os
from typing import Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class ResponseBuilder:
    """Build structured responses from retrieved data using OpenAI GPT-4."""
    
    def __init__(self, model_name: str = "gpt-4o"):
        """
        Initialize response builder with OpenAI API.
        
        Args:
            model_name: OpenAI model to use (default: gpt-4o, alternatives: gpt-4-turbo, gpt-4)
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
    
    def build_response(self, 
                      user_query: str,
                      retrieval_results: Dict,
                      conversation_history: List[Dict] = None) -> Dict:
        """
        Build a structured response from retrieval results.
        
        Args:
            user_query: Original user query
            retrieval_results: Results from Retriever (neo4j_results, milvus_results)
            conversation_history: Previous conversation messages (for context)
            
        Returns:
            Dictionary with:
            - response: Formatted response text
            - sections: Structured sections (Part Info, Model Info, PDF Excerpts)
            - pdf_urls: List of PDF URLs to display
            - sources: List of sources used
        """
        neo4j_results = retrieval_results.get('neo4j_results', {})
        milvus_results = retrieval_results.get('milvus_results', [])
        query_intent = retrieval_results.get('query_intent', 'general')  # Get the intent
        
        # Build context from retrieval results
        context = self._build_context(neo4j_results, milvus_results)
        
        print(f"\n📝 Building Response:")
        print(f"  Query Intent: {query_intent}")
        print(f"  Neo4j results: {len(neo4j_results.get('parts', []))} parts, {len(neo4j_results.get('models', []))} models")
        print(f"  Milvus results: {len(milvus_results)} PDF chunks")
        
        # Generate response using OpenAI GPT-4
        response_text = self._generate_response(
            user_query,
            context,
            conversation_history,
            query_intent  # Pass intent to guide the response
        )
        
        # Extract PDF URLs ONLY from the entities that were queried
        pdf_urls = self._extract_relevant_pdf_urls(neo4j_results, milvus_results, query_intent)
        
        print(f"  Extracted {len(pdf_urls)} relevant PDF URLs for {query_intent} query")
        if pdf_urls:
            for i, url in enumerate(pdf_urls[:3], 1):
                print(f"    [{i}] {url[:80]}...")
        
        # Build structured sections
        sections = self._build_sections(neo4j_results, milvus_results, response_text)
        
        return {
            'response': response_text,
            'sections': sections,
            'pdf_urls': pdf_urls,
            'sources': self._build_sources(neo4j_results, milvus_results)
        }
    
    def _build_context(self, neo4j_results: Dict, milvus_results: List[Dict]) -> str:
        """Build context string from retrieval results."""
        context_parts = []
        
        # Neo4j structured data
        if neo4j_results.get('parts'):
            context_parts.append("## Part Information:")
            for part in neo4j_results['parts']:
                props = part.get('properties', {})
                context_parts.append(f"- Parts Town #: {part.get('parts_town_number', props.get('Parts Town #', props.get('name', 'N/A')))}")
                context_parts.append(f"  Manufacturer #: {props.get('Manufacturer_number', props.get('Manufacture #', props.get('Manufacturer #', 'N/A')))}")
                context_parts.append(f"  Part Description: {props.get('Part', props.get('Description', 'N/A'))}")
                if part.get('models'):
                    context_parts.append(f"  Used in Models: {', '.join(part['models'])}")
                if part.get('pdf_urls'):
                    context_parts.append(f"  PDF Manuals Available: YES")
                    context_parts.append(f"  PDF URLs: {', '.join(part['pdf_urls'])}")
                else:
                    context_parts.append(f"  PDF Manuals Available: NO")
                context_parts.append("")
        
        if neo4j_results.get('models'):
            context_parts.append("## Model Information:")
            for model in neo4j_results['models']:
                props = model.get('properties', {})
                context_parts.append(f"- Model Name: {model.get('model_name', props.get('name', 'N/A'))}")
                
                # Show parts information
                if model.get('parts_town_numbers'):
                    parts_list = model.get('parts_town_numbers', [])
                    remaining = model.get('remaining_parts', 0)
                    show_all = model.get('show_all', False)
                    
                    context_parts.append("  Parts included in this model:")
                    
                    # Show all Parts Town # from the list
                    for ptn in parts_list:
                        context_parts.append(f"  - {ptn}")
                    
                    # If there are remaining parts, show "and X more"
                    if remaining > 0:
                        context_parts.append(f"  and {remaining} more")
                    
                    context_parts.append("")
                
                # Legacy support: if old format is used
                elif model.get('parts'):
                    context_parts.append(f"  Parts: {', '.join(model['parts'][:10])}")
                
                context_parts.append("")
        
        # Milvus PDF excerpts - formatted as numbered list
        if milvus_results:
            context_parts.append("## PDF Manual Excerpts:")
            context_parts.append("Present these as a numbered list in format:")
            context_parts.append("'1. On page X: [summary of content]'")
            context_parts.append("")
            for i, result in enumerate(milvus_results[:5], 1):  # Limit to top 5
                context_parts.append(f"Excerpt {i}:")
                context_parts.append(f"  Page Number: {result.get('page_number', 'N/A')}")
                context_parts.append(f"  PDF URL: {result.get('pdf_url', 'N/A')}")
                context_parts.append(f"  Parts Town #: {result.get('parts_town_number', 'N/A')}")
                context_parts.append(f"  Content: {result.get('text', '')}")
                context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _generate_response(self,
                          user_query: str,
                          context: str,
                          conversation_history: List[Dict] = None,
                          query_intent: str = 'general') -> str:
        """Generate response using OpenAI GPT-4."""
        # Build system message based on query intent
        system_message = """You are a helpful assistant for Partstown Trane parts and equipment. 
Your task is to answer user questions based on the provided structured data and PDF manual excerpts.

## ⚠️ CRITICAL RULES - ACCURACY OVER EVERYTHING:
1. Use ONLY information explicitly provided in the context
2. NEVER add, infer, or create information that isn't in the provided data
3. You MAY organize, structure, and format content for clarity and readability
4. You MAY create bullet points, sections, and headings to make content understandable
5. BUT: Every fact, detail, step, or specification MUST come from the provided excerpts
6. Do NOT fill in gaps with assumptions or general knowledge
7. If information is missing, state: "This information is not available in the provided data"
8. Better to have well-organized accurate content than messy verbatim text

BALANCE: Clarity + Accuracy. Organize freely, but never fabricate.

## Response Scope:
- If the user asks about a PART: ONLY show ## Part Information and ## PDF Manual Excerpts sections
- If the user asks about a MODEL: ONLY show ## Model Information section
- If the user asks for SPECIFIC PDF INFORMATION (installation, specs, troubleshooting): Use DETAILED EXCERPT FORMAT
- DO NOT mix part and model information unless explicitly asked for both
- DO NOT show Model Information when the query is specifically about a part

## Instructions:
1. Provide a complete, well-structured answer with ONLY the information explicitly provided
2. Use the structured data from Neo4j (parts, models) as the primary source
3. NEVER fabricate or infer data - if it's not provided, don't include it

3. For GENERAL PART QUERIES (if user asks "tell me about part X"):
   - Show ONLY ## Part Information section
   - Include ONLY the part details EXPLICITLY provided in the context:
     * Parts Town # (from context only)
     * Manufacturer # (from context only - if not provided, show "N/A")
     * Part descriptions (from context only)
     * Used in Models (ONLY models listed in context)
     * PDF Manuals Available (YES/NO based on context)
     * PDF URLs (from context only - as plain text, NOT clickable links)
   - If PDF excerpts are available, create ## PDF Manual Excerpts section
   - DO NOT add any information not explicitly in the context
   - DO NOT show ## Model Information section for part queries

3b. For PDF-SPECIFIC QUERIES (installation, specs, troubleshooting, startup, operation, etc.):
   - ⚠️ CRITICAL: Use ONLY information from the PDF excerpts - content must be 100% accurate
   - You MAY organize and structure the content for readability
   - You MAY create sections, bullet points, and numbered lists to clarify
   - BUT you MUST NOT fabricate, add, or infer any information
   
   Format:
     ## [Descriptive title based on content]
     ### Page [X]
     [Organized, structured content from the excerpt]
   
   - ALLOWED (for readability):
     * Create clear section headings based on content topics
     * Add bullet points to organize multiple items
     * Use numbered lists for sequential procedures
     * Break paragraphs into logical sections
     * Add sub-headings for clarity
   
   - ABSOLUTELY FORBIDDEN (for accuracy):
     * DO NOT add information not in the excerpt
     * DO NOT infer or assume missing details
     * DO NOT combine info from different contexts
     * DO NOT add generic knowledge or "typical" procedures
     * DO NOT create steps that aren't mentioned
     * DO NOT add technical details not in the excerpt
   
   - EXAMPLE:
     PDF says: "When zone temperature rises, RTRM energizes K10 relay coil, closing K10 contacts, energizing CC2, bringing on CPR2."
     
     ✅ GOOD (Organized but accurate):
     "**First Stage:**
     - Zone temperature rises above setpoint
     - RTRM energizes K10 relay coil
     - K10 contacts close
     - CC2 is energized
     - CPR2 compressor turns on"
     
     ❌ BAD (Added info):
     "**First Stage:**
     - Check temperature sensor
     - Verify electrical connections
     - RTRM energizes K10 relay coil..."
     (Added steps not in original)

4. For MODEL QUERIES ONLY (if user asks about a specific model):
   - Show ONLY ## Model Information section
   - Use ONLY the information provided in the context:
     * Model Name (from context only)
     * Parts list (EXACTLY as provided in context - do not add or remove any)
     * If model has <= 7 parts: ALL Parts Town # are listed
     * If model has > 7 parts: First 5 Parts Town # are listed, followed by "and X more"
   - Present with heading "Parts included in this model:" and list the Parts Town # EXACTLY as provided
   - If not all parts shown: "You can ask for more details about specific parts"
   - DO NOT add any model properties or parts not in the context
   - DO NOT show ## Part Information section for model queries

5. For PDF Manual Excerpts (ONLY for general part/model queries):
   - Format as a numbered list: "1. On page X: [summary of the content]"
   - Include the page number in each point
   - Provide a brief summary ONLY of what's actually in the excerpt - do not add information
   - Example: "1. On page 12: Discusses the installation procedure for the drain pan, emphasizing proper sealing and grounding requirements."
   - Do NOT include PDF URLs in the excerpts section
   - Do NOT use "### Excerpt X:" format
   - Do NOT summarize content that isn't in the excerpt
   
5b. For PDF-SPECIFIC QUERIES (when query_intent is 'pdf_detail'):
   - ⚠️ YOU ARE A TECHNICAL WRITER - Organize PDF content for maximum clarity
   - Your job: Make technical content understandable while keeping it 100% accurate
   - DO NOT use "On page X:" format
   
   Format:
     ## [Clear, descriptive heading]
     ### Page [page number]
     [Well-organized, structured content from excerpt]
   
   ALLOWED (for clarity and readability):
   - Create section headings and sub-headings
   - Use bullet points for lists of items
   - Use numbered lists for sequential steps
   - Break dense paragraphs into logical sections
   - Add formatting (bold for emphasis, etc.)
   - Organize information by topic or function
   
   FORBIDDEN (for accuracy):
   - Adding information not in the excerpt
   - Inferring missing steps or details
   - Including "typical" or "standard" procedures
   - Combining unrelated information
   - Creating content based on general knowledge
   
   KEY RULE: Every piece of information in your response MUST come from the excerpt
   If you organize "Step 1, 2, 3" - those steps MUST be mentioned in the excerpt
   If you add a section heading - the content under it MUST be from the excerpt
   
   EXAMPLES:
   
   PDF Excerpt: "RTRM energizes K10 relay, closing contacts, energizing CC2, starting CPR2. If cooling requirement not satisfied, RTRM energizes K9 relay, de-energizes K10, bringing on CPR1."
   
   ✅ GOOD (Organized, accurate):
   "**First Stage Cooling:**
   - RTRM energizes K10 relay
   - K10 contacts close
   - CC2 is energized
   - CPR2 compressor starts
   
   **Second Stage Cooling:**
   - RTRM energizes K9 relay
   - K10 is de-energized
   - CPR1 compressor starts"
   
   ❌ BAD (Added info not in excerpt):
   "**Pre-Start Checks:**
   - Verify power supply
   - Check connections
   
   **First Stage:**
   - RTRM energizes K10 relay..."

6. PDF URLs Display Rules:
   - For PARTS: Show PDF URL as plain text in the Part Information section
   - Format: "PDF URLs: https://example.com/manual.pdf" (NOT as a clickable link)
   - Do NOT create a separate PDF URL section or list
   - Do NOT show PDF URLs in the excerpts

7. Formatting:
   - Use clear markdown with ## headers for sections
   - Use bullet points for structured data in Part/Model Information
   - Use numbered lists for PDF Manual Excerpts
   - Be concise and only show what was asked for

8. When Information is Missing:
   - If you cannot answer with the provided data, explicitly state it
   - Example: "I don't have information about [specific detail] in the available data"
   - NEVER fill gaps with assumptions, general knowledge, or fabricated content
   - Better to say "not available" than to provide incorrect information

REMEMBER: Accuracy is paramount. NO FABRICATION under any circumstances."""
        
        # Build messages array for OpenAI API
        messages = [
            {"role": "system", "content": system_message}
        ]
        
        # Add conversation history (last 10 messages to stay within token limits)
        if conversation_history:
            for msg in conversation_history[-10:]:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                # OpenAI expects 'assistant' not 'assistant'
                if role == 'assistant':
                    messages.append({"role": "assistant", "content": content})
                else:
                    messages.append({"role": "user", "content": content})
        
        # Add current context and query
        context_message = f"""## Available Information:
{context}

## User Question:
{user_query}

Please provide a helpful response based on the information above."""
        
        messages.append({"role": "user", "content": context_message})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.0,  # Set to 0 for maximum determinism and minimal creativity
                max_tokens=2000,
                stream=False  # Non-streaming for this method
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"I apologize, but I encountered an error generating the response: {str(e)}"
    
    def generate_streaming_response(self,
                                    user_query: str,
                                    context: str,
                                    conversation_history: List[Dict] = None,
                                    query_intent: str = 'general'):
        """Generate streaming response using OpenAI GPT-4 for real-time display."""
        # Build system message (same as non-streaming)
        system_message = """You are a helpful assistant for Partstown Trane parts and equipment. 
Your task is to answer user questions based on the provided structured data and PDF manual excerpts.

## ⚠️ CRITICAL RULES - ACCURACY OVER EVERYTHING:
1. Use ONLY information explicitly provided in the context
2. NEVER add, infer, or create information that isn't in the provided data
3. You MAY organize, structure, and format content for clarity and readability
4. You MAY create bullet points, sections, and headings to make content understandable
5. BUT: Every fact, detail, step, or specification MUST come from the provided excerpts
6. Do NOT fill in gaps with assumptions or general knowledge
7. If information is missing, state: "This information is not available in the provided data"
8. Better to have well-organized accurate content than messy verbatim text

BALANCE: Clarity + Accuracy. Organize freely, but never fabricate.

## Response Scope:
- If the user asks about a PART: ONLY show ## Part Information and ## PDF Manual Excerpts sections
- If the user asks about a MODEL: ONLY show ## Model Information section
- If the user asks for SPECIFIC PDF INFORMATION (installation, specs, troubleshooting): Use DETAILED EXCERPT FORMAT
- DO NOT mix part and model information unless explicitly asked for both
- DO NOT show Model Information when the query is specifically about a part

## Instructions:
1. Provide a complete, well-structured answer with ONLY the information explicitly provided
2. Use the structured data from Neo4j (parts, models) as the primary source
3. NEVER fabricate or infer data - if it's not provided, don't include it

3. For GENERAL PART QUERIES (if user asks "tell me about part X"):
   - Show ONLY ## Part Information section
   - Include ONLY the part details EXPLICITLY provided in the context:
     * Parts Town # (from context only)
     * Manufacturer # (from context only - if not provided, show "N/A")
     * Part descriptions (from context only)
     * Used in Models (ONLY models listed in context)
     * PDF Manuals Available (YES/NO based on context)
     * PDF URLs (from context only - as plain text, NOT clickable links)
   - If PDF excerpts are available, create ## PDF Manual Excerpts section
   - DO NOT add any information not explicitly in the context
   - DO NOT show ## Model Information section for part queries

3b. For PDF-SPECIFIC QUERIES (installation, specs, troubleshooting, startup, operation, etc.):
   - ⚠️ CRITICAL: Use ONLY information from the PDF excerpts - content must be 100% accurate
   - You MAY organize and structure the content for readability
   - You MAY create sections, bullet points, and numbered lists to clarify
   - BUT you MUST NOT fabricate, add, or infer any information
   
   Format:
     ## [Descriptive title based on content]
     ### Page [X]
     [Organized, structured content from the excerpt]
   
   - ALLOWED (for readability):
     * Create clear section headings based on content topics
     * Add bullet points to organize multiple items
     * Use numbered lists for sequential procedures
     * Break paragraphs into logical sections
     * Add sub-headings for clarity
   
   - ABSOLUTELY FORBIDDEN (for accuracy):
     * DO NOT add information not in the excerpt
     * DO NOT infer or assume missing details
     * DO NOT combine info from different contexts
     * DO NOT add generic knowledge or "typical" procedures
     * DO NOT create steps that aren't mentioned
     * DO NOT add technical details not in the excerpt
   
   - EXAMPLE:
     PDF says: "When zone temperature rises, RTRM energizes K10 relay coil, closing K10 contacts, energizing CC2, bringing on CPR2."
     
     ✅ GOOD (Organized but accurate):
     "**First Stage:**
     - Zone temperature rises above setpoint
     - RTRM energizes K10 relay coil
     - K10 contacts close
     - CC2 is energized
     - CPR2 compressor turns on"
     
     ❌ BAD (Added info):
     "**First Stage:**
     - Check temperature sensor
     - Verify electrical connections
     - RTRM energizes K10 relay coil..."
     (Added steps not in original)

4. For MODEL QUERIES ONLY (if user asks about a specific model):
   - Show ONLY ## Model Information section
   - Use ONLY the information provided in the context:
     * Model Name (from context only)
     * Parts list (EXACTLY as provided in context - do not add or remove any)
     * If model has <= 7 parts: ALL Parts Town # are listed
     * If model has > 7 parts: First 5 Parts Town # are listed, followed by "and X more"
   - Present with heading "Parts included in this model:" and list the Parts Town # EXACTLY as provided
   - If not all parts shown: "You can ask for more details about specific parts"
   - DO NOT add any model properties or parts not in the context
   - DO NOT show ## Part Information section for model queries

5. For PDF Manual Excerpts (ONLY for general part/model queries):
   - Format as a numbered list: "1. On page X: [summary of the content]"
   - Include the page number in each point
   - Provide a brief summary ONLY of what's actually in the excerpt - do not add information
   - Example: "1. On page 12: Discusses the installation procedure for the drain pan, emphasizing proper sealing and grounding requirements."
   - Do NOT include PDF URLs in the excerpts section
   - Do NOT use "### Excerpt X:" format
   - Do NOT summarize content that isn't in the excerpt
   
5b. For PDF-SPECIFIC QUERIES (when query_intent is 'pdf_detail'):
   - ⚠️ YOU ARE A TECHNICAL WRITER - Organize PDF content for maximum clarity
   - Your job: Make technical content understandable while keeping it 100% accurate
   - DO NOT use "On page X:" format
   
   Format:
     ## [Clear, descriptive heading]
     ### Page [page number]
     [Well-organized, structured content from excerpt]
   
   ALLOWED (for clarity and readability):
   - Create section headings and sub-headings
   - Use bullet points for lists of items
   - Use numbered lists for sequential steps
   - Break dense paragraphs into logical sections
   - Add formatting (bold for emphasis, etc.)
   - Organize information by topic or function
   
   FORBIDDEN (for accuracy):
   - Adding information not in the excerpt
   - Inferring missing steps or details
   - Including "typical" or "standard" procedures
   - Combining unrelated information
   - Creating content based on general knowledge
   
   KEY RULE: Every piece of information in your response MUST come from the excerpt
   If you organize "Step 1, 2, 3" - those steps MUST be mentioned in the excerpt
   If you add a section heading - the content under it MUST be from the excerpt
   
   EXAMPLES:
   
   PDF Excerpt: "RTRM energizes K10 relay, closing contacts, energizing CC2, starting CPR2. If cooling requirement not satisfied, RTRM energizes K9 relay, de-energizes K10, bringing on CPR1."
   
   ✅ GOOD (Organized, accurate):
   "**First Stage Cooling:**
   - RTRM energizes K10 relay
   - K10 contacts close
   - CC2 is energized
   - CPR2 compressor starts
   
   **Second Stage Cooling:**
   - RTRM energizes K9 relay
   - K10 is de-energized
   - CPR1 compressor starts"
   
   ❌ BAD (Added info not in excerpt):
   "**Pre-Start Checks:**
   - Verify power supply
   - Check connections
   
   **First Stage:**
   - RTRM energizes K10 relay..."

6. PDF URLs Display Rules:
   - For PARTS: Show PDF URL as plain text in the Part Information section
   - Format: "PDF URLs: https://example.com/manual.pdf" (NOT as a clickable link)
   - Do NOT create a separate PDF URL section or list
   - Do NOT show PDF URLs in the excerpts

7. Formatting:
   - Use clear markdown with ## headers for sections
   - Use bullet points for structured data in Part/Model Information
   - Use numbered lists for PDF Manual Excerpts
   - Be concise and only show what was asked for

8. When Information is Missing:
   - If you cannot answer with the provided data, explicitly state it
   - Example: "I don't have information about [specific detail] in the available data"
   - NEVER fill gaps with assumptions, general knowledge, or fabricated content
   - Better to say "not available" than to provide incorrect information

REMEMBER: Accuracy is paramount. NO FABRICATION under any circumstances."""
        
        # Build messages array
        messages = [
            {"role": "system", "content": system_message}
        ]
        
        if conversation_history:
            for msg in conversation_history[-10:]:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role == 'assistant':
                    messages.append({"role": "assistant", "content": content})
                else:
                    messages.append({"role": "user", "content": content})
        
        context_message = f"""## Available Information:
{context}

## User Question:
{user_query}

Please provide a helpful response based on the information above."""
        
        messages.append({"role": "user", "content": context_message})
        
        # Return streaming generator
        try:
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.0,
                max_tokens=2000,
                stream=True  # Enable streaming
            )
            
            # Generator function for streaming
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"I apologize, but I encountered an error generating the response: {str(e)}"
    
    def _build_sections(self,
                       neo4j_results: Dict,
                       milvus_results: List[Dict],
                       response_text: str) -> Dict:
        """Build structured sections from results."""
        sections = {
            'part_info': [],
            'model_info': [],
            'pdf_excerpts': []
        }
        
        # Part information
        if neo4j_results.get('parts'):
            for part in neo4j_results['parts']:
                props = part.get('properties', {})
                sections['part_info'].append({
                    'parts_town_number': part.get('parts_town_number', props.get('Parts Town #', 'N/A')),
                    'manufacturer_number': props.get('Manufacture #', props.get('Manufacturer #', 'N/A')),
                    'description': props.get('Part', props.get('Description', 'N/A')),
                    'models': part.get('models', []),
                    'pdf_urls': part.get('pdf_urls', [])
                })
        
        # Model information
        if neo4j_results.get('models'):
            for model in neo4j_results['models']:
                props = model.get('properties', {})
                sections['model_info'].append({
                    'model_name': model.get('model_name', props.get('name', 'N/A')),
                    'parts': model.get('parts', []),
                    'parts_town_numbers': model.get('parts_town_numbers', [])
                })
        
        # PDF excerpts
        if milvus_results:
            for result in milvus_results:
                sections['pdf_excerpts'].append({
                    'text': result.get('text', ''),
                    'parts_town_number': result.get('parts_town_number', ''),
                    'pdf_url': result.get('pdf_url', ''),
                    'page_number': result.get('page_number', 0),
                    'similarity': result.get('similarity', 0.0)
                })
        
        return sections
    
    def _extract_relevant_pdf_urls(self, neo4j_results: Dict, milvus_results: List[Dict], query_intent: str) -> List[str]:
        """
        Extract ONLY PDF URLs relevant to the specific entities queried.
        For part queries: only PDFs from those specific parts.
        For model queries: only PDFs from parts in that model.
        """
        pdf_urls = set()
        
        # For part queries: only extract PDFs from the queried parts
        if query_intent == 'part_info' and neo4j_results.get('parts'):
            queried_parts = {part.get('parts_town_number') for part in neo4j_results['parts']}
            
            # Get PDFs from Neo4j part results
            for part in neo4j_results['parts']:
                part_pdf_urls = part.get('pdf_urls', [])
                for pdf_url in part_pdf_urls:
                    if pdf_url and pdf_url.strip():
                        pdf_urls.add(pdf_url)
            
            # Get PDFs from Milvus, but ONLY for the queried parts
            for result in milvus_results:
                result_part = result.get('parts_town_number', '')
                pdf_url = result.get('pdf_url', '')
                if result_part in queried_parts and pdf_url and pdf_url.strip():
                    pdf_urls.add(pdf_url)
        
        # For model queries: extract PDFs from the model's parts
        elif query_intent == 'model_info' and neo4j_results.get('models'):
            # Get all parts in the queried models
            model_parts = set()
            for model in neo4j_results['models']:
                model_parts.update(model.get('parts_town_numbers', []))
            
            # Only include PDFs from Milvus that belong to parts in the queried models
            for result in milvus_results:
                result_part = result.get('parts_town_number', '')
                pdf_url = result.get('pdf_url', '')
                if result_part in model_parts and pdf_url and pdf_url.strip():
                    pdf_urls.add(pdf_url)
        
        # For general queries: include all PDFs (fallback)
        else:
            for result in milvus_results:
                pdf_url = result.get('pdf_url', '')
                if pdf_url and pdf_url.strip():
                    pdf_urls.add(pdf_url)
            
            if neo4j_results.get('parts'):
                for part in neo4j_results['parts']:
                    part_pdf_urls = part.get('pdf_urls', [])
                    for pdf_url in part_pdf_urls:
                        if pdf_url and pdf_url.strip():
                            pdf_urls.add(pdf_url)
        
        return list(pdf_urls)
    
    def _build_sources(self, neo4j_results: Dict, milvus_results: List[Dict]) -> List[Dict]:
        """Build list of sources used."""
        sources = []
        
        # Add Neo4j sources
        if neo4j_results.get('parts') or neo4j_results.get('models'):
            sources.append({
                'type': 'Neo4j Database',
                'description': 'Structured parts and models data'
            })
        
        # Add PDF sources (extract unique URLs from milvus results)
        pdf_urls = set()
        for result in milvus_results:
            pdf_url = result.get('pdf_url', '')
            if pdf_url and pdf_url.strip():
                pdf_urls.add(pdf_url)
        
        for pdf_url in pdf_urls:
            sources.append({
                'type': 'PDF Manual',
                'url': pdf_url,
                'description': f'PDF manual excerpt'
            })
        
        return sources
