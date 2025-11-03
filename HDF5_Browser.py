import h5py
import numpy as np
import sys
import os
import tkinter as tk
from tkinter import filedialog
import ctypes


def print_help():
    """顯示輔助說明"""
    print("\n--- HDF5 互動式瀏覽器指令 ---")
    print("  ls                - 列出目前層級的群組 (Groups) 和資料集 (Datasets)")
    print("  cd <group_name>   - 進入指定的群組 (Group)")
    print("  cd ..             - 回到上一層")
    print("  cd /              - 回到根目錄")
    print("  cat <dataset_name> - 瀏覽資料集 (Dataset) 的數值和資訊")
    print("  attrs [item_name] - 顯示目前群組或指定項目 (Group/Dataset) 的屬性 (Attributes)")
    print("  pwd               - 顯示目前所在的層級路徑")
    print("  help              - 顯示此輔助說明")
    print("  exit / quit       - 離開瀏覽器")
    print("---------------------------------")

def print_ls(group):
    """列出群組內容"""
    print(f"📁 內容於: {group.name}")
    
    groups = []
    datasets = []
    
    for name, item in group.items():
        if isinstance(item, h5py.Group):
            groups.append(name)
        elif isinstance(item, h5py.Dataset):
            datasets.append(name)

    if not groups and not datasets:
        print("  (此層級為空)")
        return

    # 先印出群組 (像資料夾)
    for g in sorted(groups):
        print(f"  [GROUP]   {g}/")
        
    # 再印出資料集 (像檔案)
    for d in sorted(datasets):
        try:
            item = group[d]
            print(f"  [DATASET] {d} (Shape: {item.shape}, Dtype: {item.dtype})")
        except Exception as e:
            print(f"  [DATASET] {d} (無法讀取: {e})")

def print_dataset(dataset):
    """印出資料集的詳細資訊和數值預覽"""
    print(f"\n--- 📊 資料集: {dataset.name} ---")
    print(f"  Shape: {dataset.shape}")
    print(f"  Dtype: {dataset.dtype}")
    print(f"  Size:  {dataset.size}")
    print(f"  Chunks: {dataset.chunks}")
    print(f"  Compression: {dataset.compression}")

    # 顯示屬性
    if dataset.attrs:
        print("\n  Attributes:")
        for k, v in dataset.attrs.items():
            print(f"    - {k}: {v}")

    # 顯示數值 (使用 numpy 進行格式化，並設定預覽上限)
    print("\n  Data (預覽):")
    try:
        # 讀取所有資料 (如果檔案過大，這一步可能需要調整)
        data = dataset[()] 
        
        # 設定 numpy 的顯示選項，避免印出過多內容
        # threshold=100 表示陣列元素超過100個時就摺疊
        with np.printoptions(threshold=100, edgeitems=10):
            print(data)
            
    except TypeError:
        # 處理特殊資料類型 (例如 VLEN string)
        print(dataset[()])
    except Exception as e:
        print(f"    (無法讀取或顯示資料: {e})")
    print("--- 結束 ---")

def print_attrs(group, item_name=None):
    """印出屬性"""
    target_item = group
    if item_name:
        if item_name in group:
            target_item = group[item_name]
        else:
            print(f"錯誤: 在 '{group.name}' 中找不到 '{item_name}'")
            return

    print(f"\n--- 📋 屬性 (Attributes) 於: {target_item.name} ---")
    if not target_item.attrs:
        print("  (沒有屬性)")
        return
        
    for k, v in target_item.attrs.items():
        print(f"  - {k}: {v}")
    print("------------------------------------------")


def browse_hdf5(filepath):
    """主瀏覽器迴圈"""
    try:
        f = h5py.File(filepath, 'r')
    except Exception as e:
        print(f"錯誤: 無法開啟檔案 '{filepath}'. {e}")
        return

    current_group = f['/'] # 從根目錄開始
    filename = os.path.basename(filepath)

    print(f"成功開啟檔案: {filename}")
    print("輸入 'help' 查看所有指令。")

    while True:
        # 建立提示符號
        prompt = f"[{filename}:{current_group.name}]> "
        
        try:
            # 讀取使用者輸入
            command_line = input(prompt).strip()
            if not command_line:
                continue
            
            parts = command_line.split()
            cmd = parts[0].lower()
            args = parts[1:]

        except EOFError:
            print("\n偵測到 EOF，離開中...")
            break
        except KeyboardInterrupt:
            print("\n偵測到中斷，離開中...")
            break

        # --- 指令解析 ---
        if cmd in ['exit', 'quit', 'q']:
            print("離開瀏覽器。")
            break

        elif cmd == 'help':
            print_help()

        elif cmd == 'ls':
            print_ls(current_group)

        elif cmd == 'pwd':
            print(current_group.name)

        elif cmd == 'cd':
            if not args:
                print("錯誤: 'cd' 需要一個目標路徑。 (例如: 'cd my_group', 'cd ..', 'cd /')")
                continue
            
            target_path = " ".join(args)
            
            if target_path == '..':
                # 回到上一層
                if current_group.name == '/':
                    print("已經在根目錄了。")
                else:
                    current_group = current_group.parent
            
            elif target_path == '/':
                # 回到根目錄
                current_group = f['/']
            
            else:
                # 嘗試進入子群組
                if target_path in current_group:
                    item = current_group[target_path]
                    if isinstance(item, h5py.Group):
                        current_group = item
                    else:
                        print(f"錯誤: '{target_path}' 是一個資料集 (Dataset)，不是群組 (Group)。請使用 'cat' 查看。")
                else:
                    print(f"錯誤: 在 '{current_group.name}' 中找不到 '{target_path}'。")

        elif cmd in ['cat', 'view']:
            if not args:
                print("錯誤: 'cat' 需要一個資料集名稱。 (例如: 'cat my_data')")
                continue
                
            dataset_name = " ".join(args)
            if dataset_name in current_group:
                item = current_group[dataset_name]
                if isinstance(item, h5py.Dataset):
                    print_dataset(item)
                else:
                    print(f"錯誤: '{dataset_name}' 是一個群組 (Group)。請使用 'cd' 進入。")
            else:
                print(f"錯誤: 在 '{current_group.name}' 中找不到資料集 '{dataset_name}'。")

        elif cmd == 'attrs':
            item_name = args[0] if args else None
            print_attrs(current_group, item_name)

        else:
            print(f"錯誤: 未知的指令 '{cmd}'。 輸入 'help' 查看可用指令。")

    f.close()

def choose_file(ext = "hdf5" , save_file=False):
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # Enable high-DPI awareness
    root = tk.Tk()
    #root.attributes('-alpha',0) # Make the root window transparent
    root.attributes('-topmost', True)  # Keep the dialog on top
    root.withdraw()  # hide main window --- IGNORE ---
    path = filedialog.askopenfilename(
        title="Select an HDF5 file",
        initialdir='.',
        filetypes=[("HDF5 files", "*.h5 *.hdf5")]
    )

    return path

# Run the chooser and assign to file_path



# --- 程式執行入口 ---
if __name__ == "__main__":
    try:
        file_path = choose_file("hdf5", save_file=False)
        print("Selected file:", file_path)
        browse_hdf5(file_path)   
        
    except Exception as e:
        print(f"發生錯誤: {e}")
    
