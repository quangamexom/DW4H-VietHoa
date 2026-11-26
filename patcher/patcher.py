# -*- coding: utf-8 -*-
"""Bộ cài đặt & gỡ cài đặt bản Việt hóa Dynasty Warriors 4 Hyper (PC) — Quán Game Xóm.

Cách dùng:
  python patcher.py install [thu_muc_game]
  python patcher.py uninstall [thu_muc_game]
"""

import hashlib
import json
import os
import shutil
import struct
import sys
from pathlib import Path

BACKUP_DIR_NAME = "_backup_viethoa_dw4h"
STATE_DIR_NAME = "_viethoa_patch_state"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def apply_delta(old_bytes: bytes, delta_bytes: bytes) -> bytes:
    magic, ver, old_len, new_len = struct.unpack_from("<4sIII", delta_bytes, 0)
    if magic != b"DW4V" or ver != 1:
        raise RuntimeError("File delta không hợp lệ.")
    if len(old_bytes) != old_len:
        raise RuntimeError(f"Kích thước file gốc không khớp ({len(old_bytes)} != {old_len}).")
    expected_old = delta_bytes[16:48].hex()
    actual_old = sha256_bytes(old_bytes)
    if actual_old != expected_old:
        raise RuntimeError(
            "File gốc không khớp bản Dynasty Warriors 4 Hyper PC sạch.\n"
            f"  Thực tế : {actual_old}\n"
            f"  Yêu cầu : {expected_old}"
        )
    expected_new = delta_bytes[48:80].hex()
    n_chunks = struct.unpack_from("<I", delta_bytes, 80)[0]
    pos = 84
    out = bytearray(old_bytes)
    if new_len > old_len:
        out.extend(bytes(new_len - old_len))
    for _ in range(n_chunks):
        off, sz = struct.unpack_from("<II", delta_bytes, pos)
        pos += 8
        out[off:off + sz] = delta_bytes[pos:pos + sz]
        pos += sz
    if pos != len(delta_bytes):
        raise RuntimeError("Dữ liệu delta bị lỗi cấu trúc.")
    res = bytes(out)
    if sha256_bytes(res) != expected_new:
        raise RuntimeError("Kiểm tra SHA-256 sau khi vá EXE thất bại.")
    return res


def pick_game_folder(title: str) -> Path:
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        chosen = filedialog.askdirectory(title=title)
        root.destroy()
        if chosen:
            return Path(chosen).resolve()
    except Exception:
        pass
    entered = input("Nhập đường dẫn thư mục game Dynasty Warriors 4 Hyper: ").strip().strip('"')
    if not entered:
        raise SystemExit("Đã hủy thao tác.")
    return Path(entered).resolve()


def do_install(target: Path, here: Path) -> None:
    print("============================================================")
    print("  CÀI ĐẶT VIỆT HÓA DYNASTY WARRIORS 4 HYPER (PC) - v1.0")
    print("  Quán Game Xóm — Theo phong vị Tam Quốc Diễn Nghĩa")
    print("============================================================")
    print(f"Thư mục game: {target}\n")

    manifest_path = here / "manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError("Không tìm thấy manifest.json cạnh patcher.py.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    recipe_path = here / manifest["recipe"]
    if not recipe_path.is_file():
        raise RuntimeError(
            f"Không tìm thấy gói dữ liệu '{manifest['recipe']}'.\n"
            "Vui lòng tải gói Patch đầy đủ từ mục Releases trên GitHub và giải nén chung thư mục."
        )

    exe_p = target / "Dynasty Warriors 4 Hyper.exe"
    cfg_p = target / "DW4Config.exe"
    ld_p = target / "media/linkdata.BIN"
    idx_p = target / "media/data/etc/mdata.bin"

    for p in (exe_p, cfg_p, ld_p, idx_p):
        if not p.is_file():
            raise RuntimeError(f"Không tìm thấy file game cần thiết: {p}\nHãy chọn đúng thư mục chứa 'Dynasty Warriors 4 Hyper.exe'.")

    print("[1/5] Đang kiểm tra tính nguyên vẹn bộ game gốc (có thể mất vài giây)...")
    if sha256_file(exe_p) == manifest["patched_exe_sha256"]:
        raise RuntimeError(
            "Thư mục game này ĐÃ được cài bản Việt hóa v1.0 rồi.\n"
            "Không cần cài đè lần nữa (nếu muốn gỡ, hãy chạy GO_VIET_HOA.bat)."
        )

    for p, key in [
        (exe_p, "vanilla_exe_sha256"),
        (cfg_p, "vanilla_config_sha256"),
        (idx_p, "vanilla_mdata_sha256"),
        (ld_p, "vanilla_linkdata_sha256"),
    ]:
        actual = sha256_file(p)
        if actual != manifest[key]:
            raise RuntimeError(
                f"File '{p.name}' không khớp bản gốc sạch (English PC Hyper)!\n"
                f"  Thực tế : {actual}\n"
                f"  Yêu cầu : {manifest[key]}\n"
                "Hãy cài trên bản game gốc chưa từng chỉnh sửa."
            )

    print("[2/5] Đang kiểm tra gói vá (.gokon & .delta)...")
    if sha256_file(recipe_path) != manifest["recipe_sha256"]:
        raise RuntimeError("File .gokon bị lỗi hoặc tải thiếu. Vui lòng tải lại gói Patch.")

    sys.path.insert(0, str(here / "toolchain"))
    from GokonSoftworks.ledger import Tab
    from GokonSoftworks.recipe import read_payload, read_recipe
    from GokonSoftworks.returns import apply_recipe

    recipe = read_recipe(recipe_path)
    records = manifest["changed_linkdata_entries"]
    if len(recipe.entries) != manifest["payload_count"] or len(records) != manifest["payload_count"]:
        raise RuntimeError("Số lượng tài nguyên trong gói vá không khớp manifest.")

    for i, rec in enumerate(records):
        if recipe.entries[i].idx_marker != 0 or recipe.entries[i].entry_off != rec["entry_off"]:
            raise RuntimeError(f"Sai chỉ mục tài nguyên thứ {i}.")
        if sha256_bytes(read_payload(recipe, i)) != rec["sha256"]:
            raise RuntimeError(f"Tài nguyên thứ {i} ({rec['key']}) bị hỏng.")

    original_ld_size = ld_p.stat().st_size
    predicted_ld_size = original_ld_size + sum((rec["size"] + 2047) // 2048 * 2048 for rec in records)
    if predicted_ld_size >= 0x7FFFFFFF:
        raise RuntimeError("Kích thước linkdata.BIN sau vá vượt giới hạn 2 GiB.")

    exe_new = apply_delta(exe_p.read_bytes(), (here / "DW4H_Vietnamese_EXE.delta").read_bytes())
    cfg_new = apply_delta(cfg_p.read_bytes(), (here / "DW4H_Vietnamese_Config.delta").read_bytes())
    if sha256_bytes(exe_new) != manifest["patched_exe_sha256"]:
        raise RuntimeError("Hash EXE sau vá không khớp manifest.")
    if sha256_bytes(cfg_new) != manifest["patched_config_sha256"]:
        raise RuntimeError("Hash DW4Config sau vá không khớp manifest.")

    print("[3/5] Đang sao lưu file gốc để hỗ trợ gỡ cài đặt an toàn...")
    backup_dir = target / BACKUP_DIR_NAME
    backup_dir.mkdir(exist_ok=True)
    for rel in ("Dynasty Warriors 4 Hyper.exe", "DW4Config.exe", "media/data/etc/mdata.bin"):
        src = target / rel
        dst = backup_dir / rel
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    (backup_dir / "backup_meta.json").write_text(
        json.dumps(
            {
                "version": manifest["version"],
                "vanilla_linkdata_size": original_ld_size,
                "vanilla_linkdata_sha256": manifest["vanilla_linkdata_sha256"],
                "vanilla_exe_sha256": manifest["vanilla_exe_sha256"],
                "vanilla_config_sha256": manifest["vanilla_config_sha256"],
                "vanilla_mdata_sha256": manifest["vanilla_mdata_sha256"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("[4/5] Đang áp dụng 371 tài nguyên Việt hóa & 2 file thực thi...")
    clean_idx = idx_p.read_bytes()
    exe_p.write_bytes(exe_new)
    cfg_p.write_bytes(cfg_new)

    game = json.loads((here / "toolchain/dw4h_game.json").read_text(encoding="utf-8"))
    state_dir = target / STATE_DIR_NAME
    state_dir.mkdir(exist_ok=True)
    tab = Tab(target, "DW4H")
    tab.path = state_dir / "DW4H.tab.json"
    applied = apply_recipe(recipe, game, target, tab)
    if applied != manifest["payload_count"]:
        raise RuntimeError(f"Chỉ áp dụng được {applied}/{manifest['payload_count']} tài nguyên.")

    print("[5/5] Đang kiểm tra đọc lại toàn bộ 371/371 tài nguyên...")
    idx_after = idx_p.read_bytes()
    with ld_p.open("rb") as f:
        for rec in records:
            sec, span, size, reserved = struct.unpack_from("<4I", idx_after, rec["entry_off"])
            if reserved != 0 or size != rec["size"] or size > span * 2048:
                raise RuntimeError(f"Lỗi bảng chỉ mục cho {rec['key']}.")
            f.seek(sec * 2048)
            if sha256_bytes(f.read(size)) != rec["sha256"]:
                raise RuntimeError(f"Lỗi kiểm tra dữ liệu đã ghi cho {rec['key']}.")

    changed_offs = {rec["entry_off"] for rec in records}
    for o in range(16, len(idx_after), 16):
        if o not in changed_offs and idx_after[o:o + 16] != clean_idx[o:o + 16]:
            raise RuntimeError(f"Phát hiện thay đổi ngoài vùng cho phép tại mdata offset {o}.")

    if ld_p.stat().st_size != predicted_ld_size:
        raise RuntimeError("Kích thước linkdata.BIN sau vá không khớp dự kiến.")

    print("\n============================================================")
    print("  CÀI ĐẶT THÀNH CÔNG 100%! (371/371 tài nguyên + 2 EXE đạt)")
    print("  Bạn có thể mở 'Dynasty Warriors 4 Hyper.exe' để chơi ngay!")
    print("============================================================")


def do_uninstall(target: Path) -> None:
    print("============================================================")
    print("  GỠ CÀI ĐẶT VIỆT HÓA & KHÔI PHỤC BẢN GỐC DW4 HYPER (PC)")
    print("============================================================")
    print(f"Thư mục game: {target}\n")

    backup_dir = target / BACKUP_DIR_NAME
    meta_path = backup_dir / "backup_meta.json"
    if not meta_path.is_file():
        raise RuntimeError(f"Không tìm thấy bản sao lưu tại '{backup_dir}'. Không thể tự động gỡ.")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    for rel in ("Dynasty Warriors 4 Hyper.exe", "DW4Config.exe", "media/data/etc/mdata.bin"):
        src = backup_dir / rel
        if not src.is_file():
            raise RuntimeError(f"Thiếu file sao lưu: {src}")
        shutil.copy2(src, target / rel)

    ld_p = target / "media/linkdata.BIN"
    vanilla_size = int(meta["vanilla_linkdata_size"])
    if ld_p.stat().st_size < vanilla_size:
        raise RuntimeError("File linkdata.BIN nhỏ hơn kích thước gốc, dừng khôi phục.")
    with ld_p.open("r+b") as f:
        f.truncate(vanilla_size)

    print("Đang kiểm tra SHA-256 khôi phục toàn bộ 4 file gốc...")
    for rel, key in [
        ("Dynasty Warriors 4 Hyper.exe", "vanilla_exe_sha256"),
        ("DW4Config.exe", "vanilla_config_sha256"),
        ("media/data/etc/mdata.bin", "vanilla_mdata_sha256"),
        ("media/linkdata.BIN", "vanilla_linkdata_sha256"),
    ]:
        actual = sha256_file(target / rel)
        if actual != meta[key]:
            raise RuntimeError(f"Khôi phục '{rel}' không khớp SHA-256 gốc!")

    state_dir = target / STATE_DIR_NAME
    if state_dir.exists():
        shutil.rmtree(state_dir, ignore_errors=True)
    shutil.rmtree(backup_dir, ignore_errors=True)

    print("\n============================================================")
    print("  ĐÃ KHÔI PHỤC BẢN GAME GỐC SẠCH 100% (4/4 SHA-256 KHỚP)!")
    print("============================================================")


def main() -> None:
    here = Path(__file__).resolve().parent
    args = sys.argv[1:]
    mode = "install"
    target = None

    if args and args[0].lower() in ("install", "uninstall"):
        mode = args[0].lower()
        if len(args) >= 2:
            target = Path(args[1]).resolve()
    elif args:
        target = Path(args[0]).resolve()

    if target is None:
        title = (
            "Chọn thư mục game Dynasty Warriors 4 Hyper để CÀI VIỆT HÓA"
            if mode == "install"
            else "Chọn thư mục game Dynasty Warriors 4 Hyper để GỠ VIỆT HÓA"
        )
        target = pick_game_folder(title)

    try:
        if mode == "install":
            do_install(target, here)
        else:
            do_uninstall(target)
    except Exception as e:
        print(f"\n[LỖI] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
