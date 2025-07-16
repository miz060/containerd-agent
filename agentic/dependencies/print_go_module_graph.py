import argparse
import json
import os
import tempfile
import networkx as nx
from pathlib import Path
from go_dependencies import get_go_modules
from generate_azure_openai_training_dependencies_data import GoModuleAnalyzer




def print_module_info(modules):
    print("\nGo Modules:")
    for mod, info in modules.items():
        print(f"- {mod} (version: {info.get('version')}, type: {info.get('type')})")

def print_module_usage(modules):
    print("\nModule Usage and Definitions:")
    for mod, info in modules.items():
        defs = info.get('definition_files', [])
        uses = info.get('used_in_files', [])
        print(f"\nModule: {mod}")
        print(f"  Defined in: {defs if defs else 'N/A'}")
        print(f"  Used in: {uses if uses else 'N/A'}")

def build_dependency_graph(modules):
    G = nx.DiGraph()
    
    # Save files
    all_files = set()
    for mod, info in modules.items():
        # Add module node
        G.add_node(mod, node_type='module', module_type=info.get('type'))
        # Save
        if info.get('type') == 'internal':
            for f in info.get('definition_files', []):
                all_files.add(f)
        for f in info.get('definition_files', []):
            all_files.add(f)

    # Add file nodes
    for f in all_files:
        G.add_node(f, node_type='file')

    # Add edges
    for mod, info in modules.items():
        for f in info.get('used_in_files', []):
            G.add_edge(f, mod)
        for f in info.get('definition_files', []):
            G.add_edge(mod, f)

    # Remove external modules that are not connected (no in or out edges)
    to_remove = []
    for mod, info in modules.items():
        if info.get('type') == 'external' and G.in_degree(mod) == 0 and G.out_degree(mod) == 0:
            to_remove.append(mod)
    G.remove_nodes_from(to_remove)

    return G

def plot_graph(G, output_path=None):
    try:
        from networkx.drawing.nx_agraph import to_agraph
        import pygraphviz
    except ImportError:
        print("[ERROR] pygraphviz is required for advanced graph plotting. Please install it with 'pip install pygraphviz'.")
        return

    A = to_agraph(G)
    # Use 'neato' for a more organic layout
    A.graph_attr.update(layout='neato', bgcolor='white', overlap='false', splines='true')

    for n in G.nodes():
        node_data = G.nodes[n]
        if node_data.get('node_type') == 'module':
            module_type = node_data.get('module_type', 'internal')
            color = '#1976d2' if module_type == 'internal' else '#ff9800'
            shape = 'ellipse'
            fontcolor = '#222222'
            label = n.split('/')[-1] if '/' in n else f"{module_type} module"
        else:  # file node
            label = n.split('/')[-1] if '/' in n else "file"
            color = '#81c784'  # greenish
            shape = 'box'
            fontcolor = '#222222'
        # Update node attributes
        A.get_node(n).attr.update(
                    shape=shape,
                    style='filled',
                    fillcolor=color,
                    fontname='Arial',
                    fontcolor=fontcolor,
                    label=label
                )

    A.edge_attr.update(arrowsize='0.6', color='#607d8b')

    prog = 'neato'
    if output_path:
        A.draw(output_path, format='png', prog=prog)
        print(f"Graph saved to {output_path}")
    else:
        tmpfile = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        A.draw(tmpfile.name, format='png', prog=prog)
        tmpfile.close()
        try:
            from PIL import Image
            img = Image.open(tmpfile.name)
            img.show()
        except ImportError:
            print(f"Graph image saved to {tmpfile.name}. Please open it manually.")
        finally:
            os.unlink(tmpfile.name)

def main():
    parser = argparse.ArgumentParser(description="Analyze Go modules and optionally plot a dependency graph.")
    parser.add_argument('--repo-path', default='/workspace/upstream/containerd', help='Path to Go repository')
    parser.add_argument('--plot-graph', action='store_true', help='Plot a dependency graph (requires networkx, matplotlib)')
    parser.add_argument('--graph-output', default=None, help='Path to save the graph image (PNG)')
    args = parser.parse_args()

    modules = get_go_modules(args.repo_path)
    if not modules:
        print("No Go modules found.")
        return
    analyzer = GoModuleAnalyzer(args.repo_path)
    analyzer.analyze_go_files(modules)

    print_module_info(modules)
    print_module_usage(modules)

    if args.plot_graph:
        G = build_dependency_graph(modules)
        plot_graph(G, output_path=args.graph_output)

if __name__ == "__main__":
    main()
