import argparse
import os
import hashlib
import shutil
from collections import defaultdict
import concurrent.futures
from tqdm import tqdm

def get_file_info(path, compare_mode):
    """Gets the size and checksum of a file."""
    info = {}
    try:
        info['size'] = os.path.getsize(path)
        if compare_mode == 'checksum':
            hasher = hashlib.md5()
            with open(path, 'rb') as f:
                # Increased buffer size to 1MB
                buf = f.read(1024 * 1024)
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = f.read(1024 * 1024)
            info['checksum'] = hasher.hexdigest()
    except (IOError, OSError):
        return None
    return info

def get_directory_state(path, compare_mode, max_workers=None):
    """Recursively gets the state of a directory using parallel processing."""
    state = {}
    files_to_process = []
    
    for root, _, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, path)
            files_to_process.append((file_path, relative_path))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(get_file_info, fp, compare_mode): rp 
            for fp, rp in files_to_process
        }
        
        for future in concurrent.futures.as_completed(future_to_path):
            relative_path = future_to_path[future]
            try:
                info = future.result()
                if info:
                    state[relative_path] = info
            except Exception:
                pass
                
    return state

def compare_states(src_state, dest_state, compare_mode):
    """Compares two directory states and returns the necessary changes."""
    changes = {
        'to_copy': [],
        'to_delete': [],
        'to_replace': []
    }

    for path, src_info in src_state.items():
        dest_info = dest_state.get(path)
        if not dest_info:
            changes['to_copy'].append(path)
        elif compare_mode == 'size' and src_info['size'] != dest_info['size']:
            changes['to_replace'].append(path)
        elif compare_mode == 'checksum' and src_info.get('checksum') != dest_info.get('checksum'):
            changes['to_replace'].append(path)

    for path in dest_state:
        if path not in src_state:
            changes['to_delete'].append(path)

    return changes

def print_change_report(changes, dest_path):
    """Prints a tree-like report of the changes to be made."""
    print("\n--- Synchronization Plan ---")
    if not any(changes.values()):
        print("Directories are already in sync.")
        return

    print(f"{dest_path}/")

    all_paths = sorted(list(set(p for v in changes.values() for p in v)))
    tree = defaultdict(list)
    for path in all_paths:
        parts = path.split(os.sep)
        for i in range(len(parts)):
            parent = os.path.join(*parts[:i]) if i > 0 else '.'
            if parent not in tree:
                tree[parent] = []
            if parts[i] not in tree[parent]:
                tree[parent].append(parts[i])

    def get_change_marker(path):
        if path in changes['to_copy']:
            return '[+]'
        if path in changes['to_replace']:
            return '[~]'
        if path in changes['to_delete']:
            return '[-]'
        return '   '

    def print_tree(directory, prefix=""):
        entries = sorted(tree.get(directory, []))
        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            path = os.path.join(directory, entry) if directory != '.' else entry
            marker = get_change_marker(path)
            print(f"{prefix}{connector}{marker} {entry}")
            if path in tree:
                new_prefix = prefix + ("    " if is_last else "│   ")
                print_tree(path, new_prefix)

    print_tree('.')

def execute_change(change_type, path, src_root, dest_root, quiet=False):
    """Executes the actual file operation. Can be called from a thread."""
    src_path = os.path.join(src_root, path)
    dest_path = os.path.join(dest_root, path)

    try:
        if change_type == 'copy' or change_type == 'replace':
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(src_path, dest_path)
            if not quiet:
                print(f"Copied/Replaced '{path}'")
        elif change_type == 'delete':
            os.remove(dest_path)
            if not quiet:
                print(f"Deleted '{path}'")
    except (IOError, OSError) as e:
        # Raise exception to be caught by the main thread
        raise Exception(f"Error during {change_type} of '{path}': {e}")

def main():
    parser = argparse.ArgumentParser(description="Synchronize two directories.")
    parser.add_argument('--src', required=True, help="Source directory path.")
    parser.add_argument('--dest', required=True, help="Destination directory path.")
    parser.add_argument('--compare_mode', choices=['size', 'checksum'], default='size',
                        help="Comparison mode: size or checksum.")
    parser.add_argument('--dry_run', action='store_true', help="Only print changes, don't execute them.")
    parser.add_argument('--workers', type=int, default=os.cpu_count() or 4, help="Number of worker threads.")
    args = parser.parse_args()

    if not os.path.isdir(args.src):
        print(f"Source directory not found: {args.src}")
        return
    if not os.path.isdir(args.dest):
        print(f"Destination directory not found: {args.dest}")
        return

    print("Analyzing directories...")
    # Parallel scanning
    src_state = get_directory_state(args.src, args.compare_mode, args.workers)
    dest_state = get_directory_state(args.dest, args.compare_mode, args.workers)
    print(f"Scanned {len(src_state)} files in source and {len(dest_state)} files in destination.")

    changes = compare_states(src_state, dest_state, args.compare_mode)

    print_change_report(changes, args.dest)

    if args.dry_run:
        print("\n--- Dry run complete. No changes were made. ---")
        return

    if not any(changes.values()):
        return

    print("\n--- Starting synchronization ---")
    
    # Flatten all tasks
    all_tasks = []
    for path in changes['to_copy']:
        all_tasks.append(('copy', path))
    for path in changes['to_replace']:
        all_tasks.append(('replace', path))
    for path in changes['to_delete']:
        all_tasks.append(('delete', path))

    if not all_tasks:
        return

    # Interactive loop
    tasks_iter = iter(all_tasks)
    for change_type, path in tasks_iter:
        while True:
            response = input(f"{change_type.capitalize()} '{path}'? (y/n/t): ").lower()
            if response in ['y', 'n', 't']:
                break
            else:
                print("Invalid input. Please enter y, n, or t.")

        if response == 'y':
            try:
                execute_change(change_type, path, args.src, args.dest)
            except Exception as e:
                print(e)
        
        elif response == 'n':
            print(f"Skipping {change_type} of '{path}'")

        elif response == 't':
            print(f"Trusting all subsequent operations. Executing in parallel.")
            
            # Collect remaining tasks
            remaining_tasks = [(change_type, path)] + list(tasks_iter)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
                future_to_task = {
                    executor.submit(execute_change, c_type, p, args.src, args.dest, quiet=True): (c_type, p)
                    for c_type, p in remaining_tasks
                }
                
                for future in tqdm(concurrent.futures.as_completed(future_to_task), total=len(remaining_tasks), desc="Synchronizing"):
                    try:
                        future.result()
                    except Exception as exc:
                        tqdm.write(str(exc))
            
            # All done
            break

    print("Synchronization complete.")

if __name__ == "__main__":
    main()
