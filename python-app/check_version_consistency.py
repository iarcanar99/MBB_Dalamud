#!/usr/bin/env python3
"""
Version Consistency Checker for MBB Dalamud Bridge
Prevents version update mistakes by checking all files have same version
"""

import json
import re
import sys
from pathlib import Path

def check_version_consistency():
    """Check that all version references are consistent"""
    base_path = Path(__file__).parent

    # Files to check - แยกตาม development scope
    # PYTHON SIDE FILES (py development)
    mbb_file = base_path / "MBB.py"
    settings_file = base_path / "settings.py"
    readme_file = base_path / "README.md"

    # PLUGIN SIDE FILES (C# development)
    csproj_file = base_path / "DalamudMBBBridge" / "DalamudMBBBridge.csproj"
    json_file = base_path / "DalamudMBBBridge" / "DalamudMBBBridge.json"

    errors = []
    py_versions = {}  # Python side versions
    cs_versions = {}  # C# Plugin side versions

    # Check C# PLUGIN SIDE FILES
    print("🔍 CHECKING C# PLUGIN SIDE...")

    # Check .csproj file
    if csproj_file.exists():
        with open(csproj_file, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'<Version>([^<]+)</Version>', content)
            if match:
                cs_versions['csproj'] = match.group(1)
            else:
                errors.append("❌ [PLUGIN] Version not found in DalamudMBBBridge.csproj")
    else:
        errors.append("❌ [PLUGIN] DalamudMBBBridge.csproj not found")

    # Check .json file
    if json_file.exists():
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                name = data.get('Name', '')
                assembly_version = data.get('AssemblyVersion', '')

                # Extract version from Name field
                name_match = re.search(r'v(\d+\.\d+\.\d+(?:\.\d+)?)', name)
                if name_match:
                    cs_versions['json_name'] = name_match.group(1)
                else:
                    errors.append(f"❌ [PLUGIN] Version not found in JSON Name field: '{name}'")

                # Extract version from AssemblyVersion
                if assembly_version:
                    cs_versions['json_assembly'] = assembly_version
                else:
                    errors.append("❌ [PLUGIN] AssemblyVersion not found in JSON")

        except Exception as e:
            errors.append(f"❌ [PLUGIN] Error reading JSON file: {e}")
    else:
        errors.append("❌ [PLUGIN] DalamudMBBBridge.json not found")

    # Check PYTHON SIDE FILES
    print("🐍 CHECKING PYTHON SIDE...")

    # Check MBB.py version
    if mbb_file.exists():
        with open(mbb_file, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                py_versions['mbb_py'] = match.group(1)
            else:
                errors.append("❌ [PYTHON] __version__ not found in MBB.py")
    else:
        errors.append("❌ [PYTHON] MBB.py not found")

    # Check settings.py version
    if settings_file.exists():
        with open(settings_file, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'MagicBabel Dalamud v([0-9\.]+)', content)
            if match:
                py_versions['settings_py'] = match.group(1)
            else:
                errors.append("❌ [PYTHON] Version not found in settings.py")
    else:
        errors.append("❌ [PYTHON] settings.py not found")

    # Check README.md version
    if readme_file.exists():
        with open(readme_file, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'# MBB Dalamud Bridge v([0-9\.]+)', content)
            if match:
                py_versions['readme_md'] = match.group(1)
            else:
                errors.append("❌ [PYTHON] Version not found in README.md")
    else:
        errors.append("❌ [PYTHON] README.md not found")

    # Check consistency within each side
    py_consistent = len(set(py_versions.values())) <= 1 if py_versions else True
    cs_consistent = len(set(cs_versions.values())) <= 1 if cs_versions else True

    print("\n📝 FOUND VERSIONS:")
    print("🐍 PYTHON SIDE:")
    for file_type, version in py_versions.items():
        print(f"   {file_type}: v{version}")

    print("🔧 PLUGIN SIDE (C#):")
    for file_type, version in cs_versions.items():
        print(f"   {file_type}: v{version}")

    # Check for inconsistencies
    if not py_consistent:
        errors.append("❌ PYTHON SIDE VERSION MISMATCH!")

    if not cs_consistent:
        errors.append("❌ PLUGIN SIDE VERSION MISMATCH!")

    # Print results
    print("\n🔍 VERSION CONSISTENCY CHECK")
    print("=" * 60)
    print("📋 UPDATE PROTOCOL:")
    print("   🐍 Python changes → Update Python side only")
    print("   🔧 Plugin changes → Update Plugin side only")
    print("   🔄 Both changed → Update both sides")
    print("=" * 60)

    if errors:
        print("❌ ERRORS FOUND:")
        for error in errors:
            print(f"   {error}")
        print("\n🚨 FIX INCONSISTENCIES BEFORE BUILDING!")
        return False
    else:
        print("✅ VERSION CONSISTENCY VERIFIED")
        if py_versions:
            py_ver = list(py_versions.values())[0]
            print(f"   🐍 Python Side: v{py_ver}")
        if cs_versions:
            cs_ver = list(cs_versions.values())[0]
            print(f"   🔧 Plugin Side: v{cs_ver}")
        print("🚀 Safe to build!")
        return True

def suggest_next_version():
    """Suggest next version increment"""
    # Get current version
    json_file = Path(__file__).parent / "DalamudMBBBridge" / "DalamudMBBBridge.json"
    if json_file.exists():
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            name = data.get('Name', '')
            match = re.search(r'v(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?', name)
            if match:
                groups = match.groups()
                if groups[3]:  # Four-part version (x.y.z.w)
                    major, minor, patch, build = map(int, groups)
                    next_version = f"{major}.{minor}.{patch}.{build + 1}"
                else:  # Three-part version (x.y.z)
                    major, minor, patch = map(int, groups[:3])
                    next_version = f"{major}.{minor}.{patch + 1}"
                print(f"\n💡 SUGGESTED NEXT VERSION: v{next_version}")
                print(f"🚨 REMEMBER: Only increment by 0.0.1 (patch/build level only)")

if __name__ == "__main__":
    success = check_version_consistency()
    if success and len(sys.argv) > 1 and sys.argv[1] == "--suggest":
        suggest_next_version()

    sys.exit(0 if success else 1)