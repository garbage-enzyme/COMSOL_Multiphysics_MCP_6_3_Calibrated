"""
Test script for COMSOL MCP Server tools.
Run this while the MCP server is running in another terminal.
"""

import sys
sys.path.insert(0, ".")


def test_versioning():
    """Test version naming utilities."""
    from src.utils.versioning import (
        generate_version_name,
        generate_version_path,
        parse_version_info,
    )
    
    print("\n" + "=" * 50)
    print("Testing Versioning Utilities")
    print("=" * 50)
    
    name = generate_version_name("capacitor.mph")
    print(f"  generate_version_name('capacitor.mph') = {name}")
    
    info = parse_version_info(name)
    print(f"  parse_version_info('{name}') = {info}")
    assert info is not None, "Should parse versioned name"
    assert info["base_name"] == "capacitor"
    
    path = generate_version_path("D:/models/sim.mph")
    print(f"  generate_version_path('D:/models/sim.mph') = {path}")
    
    print("  [PASS] Versioning tests passed!")


def test_session_manager():
    """Test SessionManager singleton."""
    from src.tools.session import SessionManager
    
    print("\n" + "=" * 50)
    print("Testing SessionManager")
    print("=" * 50)
    
    sm1 = SessionManager()
    sm2 = SessionManager()
    assert sm1 is sm2, "SessionManager should be singleton"
    print("  [PASS] SessionManager is singleton")
    
    assert sm1.client is None, "Client should be None initially"
    assert not sm1.is_connected, "Should not be connected initially"
    print("  [PASS] Initial state is correct")


def test_tools_without_comsol():
    """Test tool functions without COMSOL."""
    from src.tools.session import session_manager
    from src.knowledge.embedded import list_docs, get_physics_guide, get_troubleshoot
    
    print("\n" + "=" * 50)
    print("Testing Tools (without COMSOL)")
    print("=" * 50)
    
    # Session status via session_manager
    status = session_manager.get_status()
    print(f"  session_manager.get_status() = {status}")
    assert status["connected"] is False
    print("  [PASS] session_manager returns disconnected")
    
    # Docs list
    result = list_docs()
    print(f"  list_docs() = success={result['success']}, count={result['count']}")
    assert result["success"] is True
    print(f"  [PASS] list_docs returns {result['count']} topics")
    
    # Physics guide
    result = get_physics_guide("electrostatics")
    print(f"  get_physics_guide('electrostatics') = success={result['success']}")
    assert result["success"] is True
    print("  [PASS] get_physics_guide works")
    
    # Troubleshoot
    result = get_troubleshoot("mesh_failed")
    print(f"  get_troubleshoot('mesh_failed') = success={result['success']}")
    assert result["success"] is True
    print("  [PASS] get_troubleshoot works")


def test_knowledge_tools():
    """Test knowledge base tools."""
    from src.knowledge.embedded import get_docs, list_docs, get_physics_guide
    
    print("\n" + "=" * 50)
    print("Testing Knowledge Tools")
    print("=" * 50)
    
    # List docs
    result = list_docs()
    print(f"  Available topics: {[t['name'] for t in result['topics']]}")
    
    # Get mph_api doc
    result = get_docs("mph_api")
    if result["success"]:
        print(f"  mph_api doc length: {len(result['content'])} chars")
        print("  [PASS] mph_api doc loaded")
    
    # Get physics guide
    result = get_docs("physics_guide")
    if result["success"]:
        print(f"  physics_guide doc length: {len(result['content'])} chars")
        print("  [PASS] physics_guide doc loaded")
    
    # Get workflow
    result = get_docs("workflow")
    if result["success"]:
        print(f"  workflow doc length: {len(result['content'])} chars")
        print("  [PASS] workflow doc loaded")


def main():
    print("=" * 50)
    print("COMSOL MCP Server - Tool Tests")
    print("=" * 50)
    
    try:
        test_versioning()
        test_session_manager()
        test_tools_without_comsol()
        test_knowledge_tools()
        
        print("\n" + "=" * 50)
        print("ALL TESTS PASSED!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("""
To test with COMSOL:
  1. Ensure COMSOL Multiphysics is installed
  2. Run: python -m src.server
  3. Connect with MCP client (opencode, Claude Desktop, etc.)
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
