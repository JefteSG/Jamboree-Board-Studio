import os

from jamboree_board_studio.services.workspace_service import (
    calculate_checksum_for_directory,
    compute_repack_instructions,
    export_package_paths,
    is_valid_workspace_name,
    list_workspaces,
)


def _write(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def test_checksum_is_stable_across_calls(tmp_path):
    _write(os.path.join(str(tmp_path), "a", "one.json"), "hello")
    _write(os.path.join(str(tmp_path), "b", "two.json"), "world")

    first = calculate_checksum_for_directory(str(tmp_path))
    second = calculate_checksum_for_directory(str(tmp_path))

    assert first == second
    assert len(first) == 64  # sha256 hex digest


def test_checksum_changes_when_content_changes(tmp_path):
    file_path = os.path.join(str(tmp_path), "data.json")
    _write(file_path, "hello")
    before = calculate_checksum_for_directory(str(tmp_path))

    _write(file_path, "goodbye")
    after = calculate_checksum_for_directory(str(tmp_path))

    assert before != after


def test_valid_workspace_names():
    assert is_valid_workspace_name("MyBoard") is True
    assert is_valid_workspace_name("  MyBoard  ") is True


def test_invalid_workspace_names_are_rejected():
    assert is_valid_workspace_name("") is False
    assert is_valid_workspace_name("   ") is False
    assert is_valid_workspace_name(".") is False
    assert is_valid_workspace_name("..") is False
    assert is_valid_workspace_name("../evil") is False
    assert is_valid_workspace_name("a/b") is False


def test_list_workspaces_returns_only_directories(tmp_path):
    os.makedirs(os.path.join(str(tmp_path), "WorkspaceA"))
    os.makedirs(os.path.join(str(tmp_path), "WorkspaceB"))
    _write(os.path.join(str(tmp_path), "not_a_workspace.txt"), "x")

    workspaces = list_workspaces(str(tmp_path))

    assert set(workspaces) == {"WorkspaceA", "WorkspaceB"}


def test_list_workspaces_empty_directory(tmp_path):
    assert list_workspaces(str(tmp_path)) == []


def test_compute_repack_instructions_finds_changed_and_new_files(tmp_path):
    core_dir = os.path.join(str(tmp_path), "CORE")
    workspace = os.path.join(str(tmp_path), "workspace")

    _write(os.path.join(core_dir, "bd~bd01.nx", "data", "unchanged.json"), "same")
    _write(os.path.join(core_dir, "bd~bd01.nx", "data", "changed.json"), "original")

    _write(os.path.join(workspace, "bd~bd01.nx", "data", "unchanged.json"), "same")
    _write(os.path.join(workspace, "bd~bd01.nx", "data", "changed.json"), "edited")
    _write(os.path.join(workspace, "bd~bd02.nx", "data", "new_file.json"), "brand new")

    instructions = compute_repack_instructions(workspace, core_dir)

    assert "bd~bd01.nx" in instructions
    changed_sources = {i["source"] for i in instructions["bd~bd01.nx"]}
    assert os.path.join(workspace, "bd~bd01.nx", "data", "changed.json") in changed_sources
    assert (
        os.path.join(workspace, "bd~bd01.nx", "data", "unchanged.json")
        not in changed_sources
    )

    assert "bd~bd02.nx" in instructions  # missing from CORE entirely -> counts as changed


def test_compute_repack_instructions_empty_when_nothing_changed(tmp_path):
    core_dir = os.path.join(str(tmp_path), "CORE")
    workspace = os.path.join(str(tmp_path), "workspace")
    _write(os.path.join(core_dir, "bd~bd01.nx", "data", "same.json"), "identical")
    _write(os.path.join(workspace, "bd~bd01.nx", "data", "same.json"), "identical")

    instructions = compute_repack_instructions(workspace, core_dir)

    assert instructions == {}


def test_export_package_paths_covers_smm_ryujinx_and_yuzu():
    paths = export_package_paths("/out", "MyBoard")

    assert len(paths) == 3
    assert any("Simple Mod Manager (SMM)" in p for p in paths)
    assert any("RYUJINX" in p for p in paths)
    assert any("YUZU" in p for p in paths)
    assert all(p.endswith("romfs") for p in paths)
    assert all("MyBoard" in p for p in paths)
    assert all("0100965017338000" in p for p in paths)  # game's title ID
