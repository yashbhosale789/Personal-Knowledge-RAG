import os
import re
from logging import logger

# Core Configuration
OUTPUT_FILE = "project_context.dot"
IGNORE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".venv",
    "venv",
    "env",
    "target",
}
VALID_EXTENSIONS = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".py",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".cs",
    ".java",
}


def sanitize_node_name(path):
    """Converts a file path into a clean, valid Graphviz identifier."""
    safe = re.sub(r"[^a-zA-Z0-9]", "_", path)
    return f"node_{safe}"


def parse_dependencies(file_path, base_dir):
    """Parses a file to extract import paths and resolve them to local files."""
    deps = []
    if not os.path.exists(file_path):
        return deps

    _, ext = os.path.splitext(file_path)
    current_dir = os.path.dirname(file_path)

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Match common JS/TS import patterns using triple-quoted raw string
        matches = re.findall(
            r"""(?:import|from|require\s*\(?)\s*['"]([\.\/][^'"]+)['"]""", content
        )

        for match in matches:
            # Resolve relative paths
            target_path = os.path.normpath(os.path.join(current_dir, match))
            rel_target = os.path.relpath(target_path, base_dir)

            # Check if it matches an actual file or needs extension matching
            if os.path.exists(target_path) and os.path.isfile(target_path):
                deps.append(rel_target)
            else:
                # Try common extensions
                for e in VALID_EXTENSIONS:
                    if os.path.exists(target_path + e):
                        deps.append(os.path.relpath(target_path + e, base_dir))
                        break
                    elif os.path.exists(os.path.join(target_path, f"index{e}")):
                        deps.append(
                            os.path.relpath(
                                os.path.join(target_path, f"index{e}"), base_dir
                            )
                        )
                        break

        # Support Python module import resolution
        if ext == ".py":
            py_matches = re.findall(r"(?:from|import)\s+([\.\w]+)", content)
            for m in py_matches:
                mod_path = m.replace(".", os.sep)
                possible_paths = [
                    os.path.join(current_dir, mod_path + ".py"),
                    os.path.join(current_dir, mod_path, "__init__.py"),
                    os.path.join(base_dir, mod_path + ".py"),
                    os.path.join(base_dir, mod_path, "__init__.py"),
                ]
                for p in possible_paths:
                    if os.path.exists(p) and os.path.isfile(p):
                        deps.append(os.path.relpath(p, base_dir))
                        break
    except Exception as e:  # noqa: BLE001
        logger.debug(f"Skipping unreadable dependency file: {e}")
    return deps


def build_project_graph():
    """Scans the workspace, structures subgraphs, maps dependencies, and writes the DOT file."""
    base_dir = os.getcwd()
    all_files = {}

    # Step 1: Discover all project files
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]

        for file in files:
            _, ext = os.path.splitext(file)
            if ext in VALID_EXTENSIONS:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, base_dir)
                all_files[rel_path] = {
                    "name": file,
                    "node": sanitize_node_name(rel_path),
                    "dir": os.path.dirname(rel_path),
                    "deps": [],
                }

    # Step 2: Parse imports for valid files
    for rel_path, meta in all_files.items():
        resolved_deps = parse_dependencies(os.path.join(base_dir, rel_path), base_dir)
        meta["deps"] = [d for d in resolved_deps if d in all_files and d != rel_path]

    # Step 3: Compile into Graphviz DOT syntax string
    dot_lines = [
        "digraph CodebaseArchitecture {",
        "    // Graph Styling Architecture",
        "    rankdir=LR;",
        "    splines=true;",
        "    overlap=false;",
        "    nodesep=0.4;",
        "    ranksep=0.7;",
        '    node [shape=box, style="rounded,filled", fillcolor="#f8f9fa", color="#6c757d", fontname="Helvetica", fontsize=11, margin=0.15];',
        '    edge [color="#adb5bd", arrowsize=0.6, fontname="Helvetica", fontsize=9];\n',
        "    // ==========================================",
        "    // 1. MODULE CLUSTERS & WORKSPACE DIRECTORIES",
        "    // ==========================================",
    ]

    # Group files by directory clusters
    dir_groups = {}
    for rel_path, meta in all_files.items():
        dir_groups.setdefault(meta["dir"], []).append(meta)

    cluster_counter = 0
    for directory, items in dir_groups.items():
        if directory == "":  # Root level files
            for item in items:
                dot_lines.append(
                    f'    {item["node"]} [label="📄 {item["name"]}", fillcolor="#fff3cd", color="#ffc107"];'
                )
        else:
            cluster_name = f"cluster_{cluster_counter}"
            cluster_counter += 1
            dot_lines.append(f"    subgraph {cluster_name} {{")
            dot_lines.append(f'        label="📁 {directory.replace(os.sep, "/")}";')
            dot_lines.append('        style="filled,dashed";')
            dot_lines.append('        color="#e9ecef";')
            dot_lines.append('        fillcolor="#f1f3f5";')
            for item in items:
                dot_lines.append(f'        {item["node"]} [label="📄 {item["name"]}"];')
            dot_lines.append("    }")

    dot_lines.append("    // ==========================================")
    dot_lines.append("    // 2. DEPENDENCY MAP LINKS")
    dot_lines.append("    // ==========================================")

    # Write structural edge links
    edge_seen = set()
    for rel_path, meta in all_files.items():
        for dep in meta["deps"]:
            dep_meta = all_files[dep]
            edge_str = f'    {meta["node"]} -> {dep_meta["node"]};'
            if edge_str not in edge_seen:
                dot_lines.append(
                    f'    {meta["node"]} -> {dep_meta["node"]} [label="imports"];'
                )
                edge_seen.add(edge_str)

    dot_lines.append("}")

    # Write data output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(dot_lines))
    print(f"Graph compilation complete. Codebase context written to: {OUTPUT_FILE}")


if __name__ == "__main__":
    build_project_graph()

# Git push on 30th Sep for 28th Sep