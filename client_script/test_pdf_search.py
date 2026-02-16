"""Test PDF search functionality."""

import sys
sys.path.insert(0, ".")

from src.knowledge.embedded import get_pdf_search, get_pdf_search_status, get_pdf_list_modules

print("=" * 60)
print("Testing PDF Search Tools")
print("=" * 60)

# Test status
print("\n[1] PDF Search Status:")
status = get_pdf_search_status()
print(f"    Status: {status.get('status')}")
print(f"    All deps installed: {status.get('all_deps_installed')}")

if status.get('vector_store'):
    vs = status['vector_store']
    print(f"    Documents indexed: {vs.get('count', 0)}")
    print(f"    Modules: {vs.get('module_count', 0)}")

# Test search
print("\n[2] Testing Search:")
query = "how to set boundary conditions for electrostatics"
print(f"    Query: '{query}'")
results = get_pdf_search(query, n_results=3)
print(f"    Success: {results.get('success')}")
print(f"    Results count: {results.get('count', 0)}")

if results.get('success'):
    for i, r in enumerate(results.get('results', [])[:3]):
        preview = r['text'][:80].encode('ascii', 'replace').decode('ascii')
        print(f"    [{i+1}] Module: {r['module']}, Score: {r['score']:.3f}")
        print(f"        {preview}...")

# Test module filter
print("\n[3] Testing Module Filter:")
query = "heat transfer convection"
module = "Heat_Transfer_Module"
print(f"    Query: '{query}'")
print(f"    Module: {module}")
results = get_pdf_search(query, n_results=2, module=module)
print(f"    Success: {results.get('success')}")
print(f"    Results count: {results.get('count', 0)}")

# List modules
print("\n[4] Available Modules:")
modules = get_pdf_list_modules()
if modules.get('success'):
    for m in modules['modules'][:10]:
        print(f"    - {m['name']} ({m['file_count']} files)")
    if modules['count'] > 10:
        print(f"    ... and {modules['count'] - 10} more")

print("\n" + "=" * 60)
print("PDF Search Test Complete!")
print("=" * 60)
