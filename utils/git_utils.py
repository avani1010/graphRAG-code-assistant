import subprocess
import os
from pathlib import Path


def clone_repo(repo_url, target_dir) -> Path:
    target_path = Path(target_dir)

    # if target_path.exists():
    #     print(f"Directory {target_dir} already exists, skipping clone")
    #     return target_path

    print(f"Cloning {repo_url}...")
    result = subprocess.run(
        ["git", "clone", repo_url, target_dir],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"✓ Cloned successfully to {target_dir}")
        return target_path
    else:
        raise Exception(f"Git clone failed: {result.stderr}")


def get_code_files(repo_path, language_map, skip_dirs):
    code_files = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for file in files:
            for ext, lang in language_map.items():
                if file.endswith(ext):
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(repo_path)
                    code_files.append((str(relative_path), lang, file_path))
                    break

    return code_files