#!/usr/bin/env python3
"""
Utility functions for Q&A allocation based on priority scores.
Used by both issue-miner and code-scanner components.
"""

from typing import List, Dict, Any, Union


def calculate_qa_allocation(
    items: List[Dict[str, Any]], 
    max_qa_entries: int,
    priority_field: str = "priority_score",
    id_field: str = "number"
) -> Dict[Union[int, str], int]:
    """
    Calculate weighted allocation of Q&A pairs based on priority scores.
    
    Args:
        items: List of items (issues, files, etc.) with priority scores
        max_qa_entries: Maximum total Q&A entries to allocate
        priority_field: Field name containing the priority score
        id_field: Field name containing the unique identifier
        
    Returns:
        Dictionary mapping item IDs to Q&A pair counts
    """
    if not items:
        return {}
    
    # Sort items by priority score in descending order to ensure higher priority gets more
    sorted_items = sorted(items, key=lambda x: x[priority_field], reverse=True)
    
    # Calculate total priority score
    total_priority = sum(item[priority_field] for item in sorted_items)
    
    if total_priority == 0:
        # If all priorities are 0, distribute evenly
        qa_per_item = max(1, max_qa_entries // len(sorted_items))
        return {item[id_field]: qa_per_item for item in sorted_items[:max_qa_entries]}
    
    # Calculate weighted allocation
    allocation = {}
    allocated_so_far = 0
    
    # First pass: calculate proportional allocation
    for item in sorted_items:
        weight = item[priority_field] / total_priority
        qa_count = max(1, int(weight * max_qa_entries))  # Minimum 1 Q&A per item
        allocation[item[id_field]] = qa_count
        allocated_so_far += qa_count
    
    # Second pass: adjust if we've exceeded the limit
    if allocated_so_far > max_qa_entries:
        # Reduce allocation starting from lowest priority items
        excess = allocated_so_far - max_qa_entries
        for item in reversed(sorted_items):  # Start from lowest priority
            if excess <= 0:
                break
            item_id = item[id_field]
            current_count = allocation[item_id]
            reduction = min(excess, current_count - 1)  # Keep at least 1
            allocation[item_id] = current_count - reduction
            excess -= reduction
    
    # Third pass: distribute any remaining slots to highest priority items
    elif allocated_so_far < max_qa_entries:
        remaining = max_qa_entries - allocated_so_far
        for item in sorted_items:  # Start from highest priority
            if remaining <= 0:
                break
            item_id = item[id_field]
            allocation[item_id] += 1
            remaining -= 1
    
    return allocation


def print_allocation_summary(
    items: List[Dict[str, Any]], 
    allocation: Dict[Union[int, str], int],
    priority_field: str = "priority_score",
    id_field: str = "number",
    title_field: str = "title",
    max_display: int = 20
) -> None:
    """
    Print a summary of Q&A allocation.
    
    Args:
        items: List of items with metadata
        allocation: Allocation dictionary from calculate_qa_allocation
        priority_field: Field name containing the priority score
        id_field: Field name containing the unique identifier
        title_field: Field name containing the title/description
        max_display: Maximum number of items to display
    """
    total_allocated = sum(allocation.values())
    print(f"📊 Allocated {total_allocated} Q&A pairs across {len(items)} items")
    
    # Sort items by priority for display
    sorted_items = sorted(items, key=lambda x: x[priority_field], reverse=True)
    
    print(f"\n📈 Q&A Allocation Summary (Top {min(max_display, len(items))}):")
    for item in sorted_items[:max_display]:
        item_id = item[id_field]
        if item_id in allocation:
            title = item.get(title_field, "No title")
            if len(title) > 60:
                title = title[:60] + "..."
            print(f"   {id_field.capitalize()} {item_id}: {allocation[item_id]} Q&A pairs (priority: {item[priority_field]:.1f}) - {title}")
    
    if len(items) > max_display:
        print(f"   ... and {len(items) - max_display} more items")


def calculate_file_priority_score(file_path: str, file_stats: Dict[str, Any]) -> float:
    """
    Calculate priority score for a code file based on various factors.
    
    Args:
        file_path: Path to the file
        file_stats: Dictionary containing file statistics
        
    Returns:
        Priority score (higher = more important)
    """
    score = 0.0
    
    # Base score from file size (larger files are more important)
    lines = file_stats.get("lines", 0)
    if lines > 0:
        score += min(lines / 100, 10)  # Cap at 10 points for very large files
    
    # Bonus for core/important directories
    path_lower = file_path.lower()
    if any(dir in path_lower for dir in ["core", "main", "server", "client", "api"]):
        score += 5
    
    # Bonus for specific file patterns
    if any(pattern in path_lower for pattern in ["manager", "controller", "service", "handler"]):
        score += 3
    
    # Bonus for Go files (since this is containerd)
    if file_path.endswith(".go"):
        score += 2
    
    # Bonus for files with many functions/types
    functions = file_stats.get("functions", 0)
    types = file_stats.get("types", 0)
    score += (functions + types) * 0.5
    
    # Bonus for files with documentation
    if file_stats.get("has_comments", False):
        score += 1
    
    # Penalty for test files (less priority for training)
    if "test" in path_lower:
        score *= 0.3
    
    # Penalty for vendor/third-party code
    if any(pattern in path_lower for pattern in ["vendor", "third_party", "external"]):
        score *= 0.1
    
    return max(score, 0.1)  # Minimum score of 0.1


def prepare_files_for_allocation(files_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Prepare files data for Q&A allocation by calculating priority scores.
    
    Args:
        files_data: List of file data dictionaries
        
    Returns:
        List of files with priority scores added
    """
    for file_data in files_data:
        file_path = file_data.get("file_path", "")
        file_stats = file_data.get("stats", {})
        
        # Calculate priority score
        priority_score = calculate_file_priority_score(file_path, file_stats)
        file_data["priority_score"] = priority_score
        
        # Add a unique identifier if not present
        if "id" not in file_data:
            file_data["id"] = file_path
    
    return files_data


def calculate_file_qa_allocation(
    files_data: List[Dict[str, Any]], 
    max_qa_entries: int,
    max_qa_per_file: int = 20,
    priority_field: str = "priority_score",
    file_path_field: str = "path"
) -> Dict[str, int]:
    """
    Calculate Q&A allocation for code files with additional constraints.
    
    Args:
        files_data: List of file data with priority scores
        max_qa_entries: Maximum total Q&A entries to allocate
        max_qa_per_file: Maximum Q&A pairs per individual file
        priority_field: Field name containing the priority score
        file_path_field: Field name containing the file path
        
    Returns:
        Dictionary mapping file paths to Q&A pair counts
    """
    if not files_data:
        return {}
    
    # Use the base allocation function
    base_allocation = calculate_qa_allocation(
        items=files_data,
        max_qa_entries=max_qa_entries,
        priority_field=priority_field,
        id_field=file_path_field
    )
    
    # Apply per-file limits
    total_allocated = 0
    for file_path, qa_count in base_allocation.items():
        if qa_count > max_qa_per_file:
            base_allocation[file_path] = max_qa_per_file
        total_allocated += base_allocation[file_path]
    
    # If we have remaining capacity after applying per-file limits, 
    # redistribute to high-priority files that are under the limit
    if total_allocated < max_qa_entries:
        remaining = max_qa_entries - total_allocated
        sorted_files = sorted(files_data, key=lambda x: x[priority_field], reverse=True)
        
        while remaining > 0:
            added_this_round = 0
            for file_data in sorted_files:
                if remaining <= 0:
                    break
                file_path = file_data[file_path_field]
                if file_path in base_allocation and base_allocation[file_path] < max_qa_per_file:
                    base_allocation[file_path] += 1
                    remaining -= 1
                    added_this_round += 1
            
            # If we couldn't add any more in this round, break to avoid infinite loop
            if added_this_round == 0:
                break
    
    return base_allocation


def validate_qa_allocation(
    allocation: Dict[Union[int, str], int],
    max_qa_entries: int,
    max_qa_per_item: int = None
) -> bool:
    """
    Validate that Q&A allocation meets constraints.
    
    Args:
        allocation: Q&A allocation dictionary
        max_qa_entries: Maximum total Q&A entries
        max_qa_per_item: Maximum Q&A pairs per item (optional)
        
    Returns:
        True if allocation is valid, False otherwise
    """
    total_allocated = sum(allocation.values())
    
    # Check total limit
    if total_allocated > max_qa_entries:
        print(f"❌ Total allocation ({total_allocated}) exceeds limit ({max_qa_entries})")
        return False
    
    # Check per-item limit
    if max_qa_per_item:
        for item_id, qa_count in allocation.items():
            if qa_count > max_qa_per_item:
                print(f"❌ Item {item_id} allocation ({qa_count}) exceeds per-item limit ({max_qa_per_item})")
                return False
    
    return True
