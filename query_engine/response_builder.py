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
        
        # Build context from retrieval results
        context = self._build_context(neo4j_results, milvus_results)
        
        # Generate response using OpenAI GPT-4
        response_text = self._generate_response(
            user_query,
            context,
            conversation_history
        )
        
        # Extract PDF URLs (only from Milvus results that were actually used)
        pdf_urls = self._extract_pdf_urls(milvus_results)
        
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
                context_parts.append(f"- Parts Town #: {part.get('parts_town_number', props.get('Parts Town #', 'N/A'))}")
                context_parts.append(f"  Manufacturer #: {props.get('Manufacture #', props.get('Manufacturer #', 'N/A'))}")
                context_parts.append(f"  Part Description: {props.get('Part', props.get('Description', 'N/A'))}")
                if part.get('models'):
                    context_parts.append(f"  Used in Models: {', '.join(part['models'])}")
                if part.get('pdf_urls'):
                    context_parts.append(f"  PDF Manuals: {', '.join(part['pdf_urls'])}")
                context_parts.append("")
        
        if neo4j_results.get('models'):
            context_parts.append("## Model Information:")
            for model in neo4j_results['models']:
                props = model.get('properties', {})
                context_parts.append(f"- Model Name: {model.get('model_name', props.get('name', 'N/A'))}")
                if model.get('parts'):
                    context_parts.append(f"  Parts: {', '.join(model['parts'][:10])}")  # Limit to first 10
                context_parts.append("")
        
        # Milvus PDF excerpts
        if milvus_results:
            context_parts.append("## PDF Manual Excerpts:")
            for i, result in enumerate(milvus_results[:5], 1):  # Limit to top 5
                context_parts.append(f"### Excerpt {i} (Page {result.get('page_number', 'N/A')}):")
                context_parts.append(result.get('text', ''))
                context_parts.append(f"Parts Town #: {result.get('parts_town_number', 'N/A')}")
                context_parts.append(f"PDF URL: {result.get('pdf_url', 'N/A')}")
                context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _generate_response(self,
                          user_query: str,
                          context: str,
                          conversation_history: List[Dict] = None) -> str:
        """Generate response using OpenAI GPT-4."""
        # Build system message
        system_message = """You are a helpful assistant for Partstown Trane parts and equipment. 
Your task is to answer user questions based on the provided structured data and PDF manual excerpts.

## Instructions:
1. Provide a clear, structured answer to the user's question
2. Use the structured data from Neo4j (parts, models) as the primary source
3. Use PDF excerpts from Milvus only when they provide relevant additional context
4. Format your response in clear sections:
   - **Part Information** (if applicable)
   - **Model Information** (if applicable)
   - **PDF Manual Excerpts** (if applicable)
5. Only mention PDF URLs if you actually reference content from those PDFs
6. If no relevant information is found, politely inform the user
7. Be concise but thorough
8. Use markdown formatting for better readability"""
        
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
                temperature=0.7,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"I apologize, but I encountered an error generating the response: {str(e)}"
    
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
    
    def _extract_pdf_urls(self, milvus_results: List[Dict]) -> List[str]:
        """Extract unique PDF URLs from Milvus results."""
        pdf_urls = set()
        for result in milvus_results:
            pdf_url = result.get('pdf_url')
            if pdf_url:
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
        
        # Add PDF sources
        pdf_urls = self._extract_pdf_urls(milvus_results)
        for pdf_url in pdf_urls:
            sources.append({
                'type': 'PDF Manual',
                'url': pdf_url,
                'description': f'PDF manual excerpt'
            })
        
        return sources
