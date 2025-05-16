from typing import Optional
from datetime import datetime
import logging
from langchain.tools import tool

from app.services.vector_service import mental_health_vector_store
from Data_Base.db_manager import store_intervention

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("knowledge_tool")

@tool
def retrieve_relevant_information(
    query: str,
    category: Optional[str] = None,
    num_results: int = 3,
    user_id: Optional[int] = 1
) -> str:
    """
    Retrieve relevant mental health information from the knowledge base.
    
    Args:
        query: User's query or need that requires information
        category: Optional category to search in (cbt_resources, psychoeducation, crisis_protocols, interventions)
        num_results: Number of results to return
        user_id: Optional user ID for tracking
        
    Returns:
        String containing relevant information
    """
    try:
        logger.info(f"Retrieving information for query: '{query}', category: '{category}'")
        
        # Check if vector store has been initialized
        if any(collection.count() == 0 for collection in mental_health_vector_store.collections.values()):
            # Try to initialize the vector store
            from app.services.vector_service import init_vector_store
            init_vector_store()
            
            # Log warning after attempted initialization
            if any(collection.count() == 0 for collection in mental_health_vector_store.collections.values()):
                msg = "Knowledge base may not be properly indexed. Check the directory structure and file contents."
                logger.warning(msg)
                return f"Warning: {msg} Using query: '{query}'"
        
        # If category is specified, search only in that category
        if category and category in ["cbt_resources", "psychoeducation", "crisis_protocols", "interventions"]:
            results = mental_health_vector_store.search_by_category(query, category, num_results)
            
            if not results:
                logger.warning(f"No results found in category '{category}' for query: '{query}'")
                return f"No relevant information found in the {_get_readable_category_name(category)} for '{query}'."
                
            # Return raw results with metadata for LLM formatting
            return _format_basic_results(results)
        
        # Otherwise, search across all collections
        results = mental_health_vector_store.query(query, n_results=num_results)
        
        # Check if any results were found
        has_results = any(len(cat_results) > 0 for cat_results in results.values())
        if not has_results:
            logger.warning(f"No results found in any category for query: '{query}'")
            return f"No relevant information found for '{query}'. Please try a different search term or check if the knowledge base is properly indexed."
        
        # Combine all results
        all_results = []
        for cat_name, cat_results in results.items():
            if cat_results:  # Only include categories with results
                category_info = {
                    "category": _get_readable_category_name(cat_name),
                    "results": cat_results
                }
                all_results.append(category_info)
        
        # Return structured but minimal formatting for LLM to process
        return _format_basic_results(all_results)
        
    except Exception as e:
        logger.error(f"Error retrieving information: {str(e)}")
        return f"Error retrieving information: {str(e)}"

@tool
def get_cbt_exercise(
    issue: str,
    distortion_type: Optional[str] = None,
    exercise_type: Optional[str] = None,
    user_context: Optional[str] = None,
    user_id: Optional[int] = 1
) -> str:
    """
    Retrieve a CBT exercise for a given issue and record the intervention.
    
    Args:
        issue: The mental health issue or symptom to address (e.g., anxiety, depression, negative thoughts)
        distortion_type: Optional cognitive distortion to address
        exercise_type: Optional specific exercise type (e.g., thought_record, behavioral_activation)
        user_context: Optional context about the user's situation
        user_id: Optional user ID for tracking
        
    Returns:
        String containing a CBT exercise
    """
    try:
        logger.info(f"Getting CBT exercise for issue: '{issue}', type: '{exercise_type}'")
        
        # Try to initialize the vector store if needed
        if mental_health_vector_store.collections["cbt_resources"].count() == 0:
            from app.services.vector_service import init_vector_store
            init_vector_store()
        
        # Record this intervention
        if user_id:
            timestamp = datetime.now().isoformat()
            try:
                store_intervention(
                    user_id=user_id,
                    intervention_type="cbt_exercise",
                    issue=issue,
                    distortion_type=distortion_type,
                    timestamp=timestamp
                )
            except Exception as e:
                logger.error(f"Failed to store intervention: {e}")
        
        # Build query based on inputs
        query = f"CBT exercise for {issue}"
        if distortion_type:
            query += f" addressing {distortion_type} distortion"
        if exercise_type:
            query += f" {exercise_type}"
        if user_context:
            query += f" relevant to {user_context}"
        
        # Get results from the CBT resources collection
        results = mental_health_vector_store.search_by_category(query, "cbt_resources", 2)
        
        if not results:
            logger.warning(f"No CBT exercises found for '{issue}'")
            return f"No CBT exercises found for {issue}. Please check the knowledge base or try with different search terms."
        
        # Return raw content with minimal formatting - let the LLM format it appropriately
        return _format_basic_results(results)
        
    except Exception as e:
        logger.error(f"Error retrieving CBT exercise: {str(e)}")
        return f"Error retrieving CBT exercise: {str(e)}"

@tool
def get_crisis_protocol(
    risk_level: str,
    user_id: Optional[int] = 1
) -> str:
    """
    Retrieve appropriate crisis protocols based on risk level.
    
    Args:
        risk_level: Level of risk (low, moderate, high, imminent)
        user_id: Optional user ID for tracking
        
    Returns:
        String containing crisis protocol information
    """
    try:
        logger.info(f"Getting crisis protocol for risk level: '{risk_level}'")
        
        # Try to initialize the vector store if needed
        if mental_health_vector_store.collections["crisis_protocols"].count() == 0:
            from app.services.vector_service import init_vector_store
            init_vector_store()
        
        # Map risk level to query terms
        risk_queries = {
            "low": "low risk suicide safety plan protocol",
            "moderate": "moderate risk suicide protocol",
            "high": "high risk suicide protocol emergency",
            "imminent": "imminent suicide risk emergency protocol"
        }
        
        if risk_level.lower() not in risk_queries:
            logger.warning(f"Invalid risk level: '{risk_level}'")
            return "Invalid risk level. Please specify low, moderate, high, or imminent."
        
        query = risk_queries[risk_level.lower()]
        
        # Get results specifically from crisis protocols
        results = mental_health_vector_store.search_by_category(query, "crisis_protocols", 2)
        
        if not results:
            logger.warning(f"No crisis protocols found for '{risk_level}' risk level")
            return f"No crisis protocols found for {risk_level} risk level. Please check the knowledge base or try with a different risk level."
        
        # Return results with minimal formatting - let the LLM format appropriately
        header = f"CRISIS PROTOCOL: {risk_level.upper()} RISK LEVEL"
        return header + "\n\n" + _format_basic_results(results)
        
    except Exception as e:
        logger.error(f"Error retrieving crisis protocol: {str(e)}")
        return f"Error retrieving crisis protocol: {str(e)}"

@tool
def get_psychoeducation(
    topic: str,
    format_type: Optional[str] = "standard",
    user_id: Optional[int] = 1
) -> str:
    """
    Retrieve psychoeducational content on a mental health topic and record the intervention.
    
    Args:
        topic: Mental health topic to get information about
        format_type: Optional format preference (brief, detailed, simple)
        user_id: Optional user ID for tracking
        
    Returns:
        String containing psychoeducational information
    """
    try:
        logger.info(f"Getting psychoeducation for topic: '{topic}', format: '{format_type}'")
        
        # Try to initialize the vector store if needed
        if mental_health_vector_store.collections["psychoeducation"].count() == 0:
            from app.services.vector_service import init_vector_store
            init_vector_store()
        
        # Record this intervention
        if user_id:
            timestamp = datetime.now().isoformat()
            try:
                store_intervention(
                    user_id=user_id,
                    intervention_type="psychoeducation",
                    topic=topic,
                    format_type=format_type,
                    timestamp=timestamp
                )
            except Exception as e:
                logger.error(f"Failed to store intervention: {e}")
        
        query = f"information about {topic} mental health education"
        
        # Get results from the psychoeducation collection
        results = mental_health_vector_store.search_by_category(query, "psychoeducation", 2)
        
        if not results:
            logger.warning(f"No psychoeducation found for topic: '{topic}', trying general search")
            # Fallback to general search if nothing found in psychoeducation
            all_results = mental_health_vector_store.query(query, n_results=2)
            for category, cat_results in all_results.items():
                if cat_results:
                    results = cat_results
                    break
        
        if not results:
            logger.warning(f"No psychoeducational information found for topic: '{topic}'")
            return f"No psychoeducational information found about {topic}. Please check the knowledge base or try with a different topic."
        
        # Return raw results with metadata and format preference
        return f"FORMAT PREFERENCE: {format_type}\n\n" + _format_basic_results(results)
        
    except Exception as e:
        logger.error(f"Error retrieving psychoeducational content: {str(e)}")
        return f"Error retrieving psychoeducational content: {str(e)}"

def _get_readable_category_name(category: str) -> str:
    """Convert internal category names to readable names"""
    category_map = {
        "cbt_resources": "CBT Exercises and Worksheets",
        "psychoeducation": "Psychoeducational Materials",
        "crisis_protocols": "Crisis Protocols and Safety Planning",
        "interventions": "Evidence-Based Interventions"
    }
    return category_map.get(category, category)

def _format_basic_results(results) -> str:
    """
    Format search results with minimal formatting, providing metadata
    for the LLM to use in its own formatting
    """
    if not results:
        return "No relevant information found."
        
    if isinstance(results, list) and results and isinstance(results[0], dict) and "category" in results[0]:
        # Handle category-organized results
        formatted = []
        for category_info in results:
            cat_name = category_info["category"]
            formatted.append(f"# CATEGORY: {cat_name}")
            
            for result in category_info["results"]:
                source = result["metadata"].get("source", "Unknown source")
                page = result["metadata"].get("page", "Unknown page")
                formatted.append(f"SOURCE: {source} | PAGE: {page}")
                formatted.append("CONTENT:")
                formatted.append(result["content"])
                formatted.append("---")
                
        return "\n\n".join(formatted)
    
    # Handle single category results
    formatted = []
    for result in results:
        source = result["metadata"].get("source", "Unknown source")
        page = result["metadata"].get("pages", result["metadata"].get("page", "Unknown page"))
        formatted.append(f"SOURCE: {source} | PAGE: {page}")
        formatted.append("CONTENT:")
        formatted.append(result["content"])
        formatted.append("---")
        
    return "\n\n".join(formatted)