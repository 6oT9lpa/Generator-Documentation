from pathlib import Path
import os

def generate_docs_for_group(group_idx, group, repo_path, file_details, docs_dir_path):
    from src.services.ai_service import AIService 

    ai_service = AIService()
    group_dir = Path(docs_dir_path) / f"group_{group_idx}"
    group_dir.mkdir(exist_ok=True)
    
    for file_path in group:
        abs_path = os.path.join(repo_path, file_path)
        if not os.path.exists(abs_path):
            continue
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            dependencies = file_details.get(file_path, {}).get("imports", [])
            documentation = ai_service.generate_documentation_sync(content, file_path, dependencies) 
            doc_path = group_dir / f"{os.path.basename(file_path)}.md"
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(documentation)
        except Exception as e:
            print(f"[!] Failed for {file_path}: {e}")