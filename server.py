import arxiv
import json
import os
from typing import List
from typing import List, Dict, Optional
from datetime import datetime
from mcp.server.fastmcp import FastMCP

PAPER_DIR = "papers"

# Initialize FastMCP server
mcp = FastMCP("research")


@mcp.tool()
def search_papers(topic: str, max_results: int = 5) -> List[str]:
    """
    Search for papers on arXiv based on a topic and store their information.

    Args:
        topic: The topic to search for
        max_results: Maximum number of results to retrieve (default: 5)

    Returns:
        List of paper IDs found in the search
    """

    # Use arxiv to find the papers
    client = arxiv.Client()

    # Search for the most relevant articles matching the queried topic
    search = arxiv.Search(
        query=topic, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance
    )

    papers = client.results(search)

    # Create directory for this topic
    path = os.path.join(PAPER_DIR, topic.lower().replace(" ", "_"))
    os.makedirs(path, exist_ok=True)

    file_path = os.path.join(path, "papers_info.json")

    # Try to load existing papers info
    try:
        with open(file_path, "r") as json_file:
            papers_info = json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError):
        papers_info = {}

    # Process each paper and add to papers_info
    paper_ids = []
    for paper in papers:
        paper_ids.append(paper.get_short_id())
        paper_info = {
            "title": paper.title,
            "authors": [author.name for author in paper.authors],
            "summary": paper.summary,
            "pdf_url": paper.pdf_url,
            "published": str(paper.published.date()),
        }
        papers_info[paper.get_short_id()] = paper_info

    # Save updated papers_info to json file
    with open(file_path, "w") as json_file:
        json.dump(papers_info, json_file, indent=2)

    print(f"Results are saved in: {file_path}")

    return paper_ids


@mcp.tool()
def extract_info(paper_id: str) -> str:
    """
    Search for information about a specific paper across all topic directories.

    Args:
        paper_id: The ID of the paper to look for

    Returns:
        JSON string with paper information if found, error message if not found
    """

    for item in os.listdir(PAPER_DIR):
        item_path = os.path.join(PAPER_DIR, item)
        if os.path.isdir(item_path):
            file_path = os.path.join(item_path, "papers_info.json")
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r") as json_file:
                        papers_info = json.load(json_file)
                        if paper_id in papers_info:
                            return json.dumps(papers_info[paper_id], indent=2)
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    print(f"Error reading {file_path}: {str(e)}")
                    continue

    return f"There's no saved information related to paper {paper_id}."


@mcp.tool()
def search_by_author(author_name: str, max_results: int = 10) -> List[Dict]:
    """
    Search for papers by a specific author on arXiv.
    Args:
        author_name: Name of the author to search for
        max_results: Maximum number of results to retrieve (default: 10)
    Returns:
        List of dictionaries containing paper information
    """
    client = arxiv.Client()
    search = arxiv.Search(
        query=f"au:{author_name}",
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
    )

    results = []
    for paper in client.results(search):
        results.append(
            {
                "id": paper.get_short_id(),
                "title": paper.title,
                "published": str(paper.published.date()),
                "summary": paper.summary[:200] + "...",
                "pdf_url": paper.pdf_url,
            }
        )

    return results


@mcp.tool()
def search_by_category(category: str, max_results: int = 10) -> List[Dict]:
    """
    Search for papers in a specific arXiv category.
    Args:
        category: arXiv category (e.g., 'cs.AI', 'cs.LG', 'math.CO')
        max_results: Maximum number of results to retrieve (default: 10)
    Returns:
        List of dictionaries containing paper information
    """
    client = arxiv.Client()
    search = arxiv.Search(
        query=f"cat:{category}",
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
    )

    results = []
    for paper in client.results(search):
        results.append(
            {
                "id": paper.get_short_id(),
                "title": paper.title,
                "authors": [author.name for author in paper.authors],
                "published": str(paper.published.date()),
                "categories": paper.categories,
            }
        )

    return results


@mcp.tool()
def get_recent_papers(days: int = 7, category: Optional[str] = None) -> List[Dict]:
    """
    Get recently published papers, optionally filtered by category.
    Args:
        days: Number of days to look back (default: 7)
        category: Optional arXiv category to filter by
    Returns:
        List of recently published papers
    """
    client = arxiv.Client()
    query = f"cat:{category}" if category else "all"

    search = arxiv.Search(
        query=query, max_results=20, sort_by=arxiv.SortCriterion.SubmittedDate
    )

    results = []
    for paper in client.results(search):
        results.append(
            {
                "id": paper.get_short_id(),
                "title": paper.title,
                "authors": [author.name for author in paper.authors][:3],
                "published": str(paper.published.date()),
                "pdf_url": paper.pdf_url,
            }
        )

    return results[:10]


@mcp.tool()
def download_paper_pdf(paper_id: str, topic: str) -> str:
    """
    Download the PDF for a specific paper.
    Args:
        paper_id: The ID of the paper to download
        topic: The topic folder where paper info is stored
    Returns:
        Path to the downloaded PDF or error message
    """
    path = os.path.join(PAPER_DIR, topic.lower().replace(" ", "_"))
    file_path = os.path.join(path, "papers_info.json")

    try:
        with open(file_path, "r") as json_file:
            papers_info = json.load(json_file)

        if paper_id not in papers_info:
            return f"Paper {paper_id} not found in topic '{topic}'"

        client = arxiv.Client()
        search = arxiv.Search(id_list=[paper_id])
        paper = next(client.results(search))

        pdf_path = os.path.join(path, f"{paper_id}.pdf")
        paper.download_pdf(filename=pdf_path)

        return f"PDF downloaded to: {pdf_path}"
    except Exception as e:
        return f"Error downloading PDF: {str(e)}"


@mcp.tool()
def compare_papers(paper_ids: List[str]) -> Dict:
    """
    Compare multiple papers side by side.
    Args:
        paper_ids: List of paper IDs to compare
    Returns:
        Dictionary with comparison information
    """
    comparison = {}

    for paper_id in paper_ids:
        for item in os.listdir(PAPER_DIR):
            item_path = os.path.join(PAPER_DIR, item)
            if os.path.isdir(item_path):
                file_path = os.path.join(item_path, "papers_info.json")
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, "r") as json_file:
                            papers_info = json.load(json_file)
                            if paper_id in papers_info:
                                comparison[paper_id] = {
                                    "title": papers_info[paper_id]["title"],
                                    "authors": papers_info[paper_id]["authors"],
                                    "published": papers_info[paper_id]["published"],
                                    "summary_length": len(
                                        papers_info[paper_id]["summary"]
                                    ),
                                }
                                break
                    except (FileNotFoundError, json.JSONDecodeError):
                        continue

    return comparison


@mcp.tool()
def list_all_topics() -> List[str]:
    """
    List all topics that have been searched and stored.
    Returns:
        List of topic names
    """
    os.makedirs(PAPER_DIR, exist_ok=True)
    topics = []
    for item in os.listdir(PAPER_DIR):
        item_path = os.path.join(PAPER_DIR, item)
        if os.path.isdir(item_path):
            topics.append(item.replace("_", " ").title())
    return topics


@mcp.tool()
def get_topic_statistics(topic: str) -> Dict:
    """
    Get statistics about papers in a specific topic.
    Args:
        topic: The topic to analyze
    Returns:
        Dictionary with statistics
    """
    path = os.path.join(PAPER_DIR, topic.lower().replace(" ", "_"))
    file_path = os.path.join(path, "papers_info.json")

    try:
        with open(file_path, "r") as json_file:
            papers_info = json.load(json_file)

        authors = set()
        categories = set()
        years = {}

        for paper in papers_info.values():
            authors.update(paper["authors"])
            if "categories" in paper:
                categories.update(paper["categories"])
            year = paper["published"][:4]
            years[year] = years.get(year, 0) + 1

        return {
            "total_papers": len(papers_info),
            "unique_authors": len(authors),
            "categories": list(categories),
            "papers_by_year": years,
            "topic": topic,
        }
    except (FileNotFoundError, json.JSONDecodeError):
        return {"error": f"No data found for topic '{topic}'"}


@mcp.tool()
def search_related_papers(paper_id: str, max_results: int = 5) -> List[Dict]:
    """
    Find papers related to a given paper based on its title and summary.
    Args:
        paper_id: The ID of the reference paper
        max_results: Maximum number of related papers to find
    Returns:
        List of related papers
    """
    # First, find the paper
    paper_info = None
    for item in os.listdir(PAPER_DIR):
        item_path = os.path.join(PAPER_DIR, item)
        if os.path.isdir(item_path):
            file_path = os.path.join(item_path, "papers_info.json")
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r") as json_file:
                        papers_info = json.load(json_file)
                        if paper_id in papers_info:
                            paper_info = papers_info[paper_id]
                            break
                except (FileNotFoundError, json.JSONDecodeError):
                    continue

    if not paper_info:
        return [{"error": f"Paper {paper_id} not found"}]

    # Search for related papers using title keywords
    title_words = paper_info["title"].split()[:5]
    query = " ".join(title_words)

    client = arxiv.Client()
    search = arxiv.Search(
        query=query, max_results=max_results + 1, sort_by=arxiv.SortCriterion.Relevance
    )

    results = []
    for paper in client.results(search):
        if paper.get_short_id() != paper_id:
            results.append(
                {
                    "id": paper.get_short_id(),
                    "title": paper.title,
                    "authors": [author.name for author in paper.authors][:3],
                    "published": str(paper.published.date()),
                    "relevance_note": "Related by topic",
                }
            )

    return results[:max_results]


@mcp.tool()
def export_bibliography(topic: str, format: str = "bibtex") -> str:
    """
    Export papers from a topic as a bibliography.
    Args:
        topic: The topic to export
        format: Bibliography format ('bibtex' or 'plain')
    Returns:
        Formatted bibliography string
    """
    path = os.path.join(PAPER_DIR, topic.lower().replace(" ", "_"))
    file_path = os.path.join(path, "papers_info.json")

    try:
        with open(file_path, "r") as json_file:
            papers_info = json.load(json_file)

        bibliography = []
        for paper_id, paper in papers_info.items():
            if format == "bibtex":
                entry = f"""@article{{{paper_id},
  title={{{paper["title"]}}},
  author={{{", ".join(paper["authors"])}}},
  year={{{paper["published"][:4]}}},
  url={{{paper["pdf_url"]}}}
}}"""
                bibliography.append(entry)
            else:
                entry = f'{", ".join(paper["authors"])}. "{paper["title"]}." ({paper["published"][:4]}). {paper["pdf_url"]}'
                bibliography.append(entry)

        return "\n\n".join(bibliography)
    except (FileNotFoundError, json.JSONDecodeError):
        return f"Error: No data found for topic '{topic}'"


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport="stdio")
