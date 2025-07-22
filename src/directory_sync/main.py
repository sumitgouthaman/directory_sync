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
                buf = f.read(65536)
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = f.read(65536)
            info['checksum'] = hasher.hexdigest()
    except (IOError, OSError):
        return None
    return info

def get_directory_state(path, compare_mode):
    """Recursively gets the state of a directory."""
    state = {}
    for root, _, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, path)
            state[relative_path] = get_file_info(file_path, compare_mode)
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
    args = parser.parse_args()

    if not os.path.isdir(args.src):
        print(f"Source directory not found: {args.src}")
        return
    if not os.path.isdir(args.dest):
        print(f"Destination directory not found: {args.dest}")
        return

    print("Analyzing directories...")
    src_state = get_directory_state(args.src, args.compare_mode)
    dest_state = get_directory_state(args.dest, args.compare_mode)
    changes = compare_states(src_state, dest_state, args.compare_mode)

    print_change_report(changes, args.dest)

    if args.dry_run:
        print("\n--- Dry run complete. No changes were made. ---")
        return

    if not any(changes.values()):
        return

    print("\n--- Starting synchronization ---")
    
    # Use a thread pool to execute file operations in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
        operation_order = [
            ('copy', changes['to_copy']),
            ('replace', changes['to_replace']),
            ('delete', changes['to_delete'])
        ]

        for change_type, paths in operation_order:
            if not paths:
                continue

            # Use an iterator to manage the list of paths
            paths_iter = iter(paths)

            for path in paths_iter:
                while True:
                    response = input(f"{change_type.capitalize()} '{path}'? (y/n/t): ").lower()
                    if response in ['y', 'n', 't']:
                        break
                    else:
                        print("Invalid input. Please enter y, n, or t.")

                if response == 'y':
                    try:
                        # Execute synchronously
                        execute_change(change_type, path, args.src, args.dest)
                    except Exception as e:
                        print(e)
                
                elif response == 'n':
                    print(f"Skipping {change_type} of '{path}'")

                elif response == 't':
                    print(f"Trusting all subsequent '{change_type}' operations. Executing in parallel.")
                    
                    # Create a list of the current path and all remaining paths from the iterator
                    remaining_paths = [path] + list(paths_iter)
                    
                    # Submit all trusted tasks to the executor
                    future_to_path = {executor.submit(execute_change, change_type, p, args.src, args.dest, quiet=True): p for p in remaining_paths}
                    
                    # Use tqdm to create a progress bar
                    for future in tqdm(concurrent.futures.as_completed(future_to_path), total=len(remaining_paths), desc=f"Processing {change_type}"):
                        try:
                            # result() will re-raise any exception from the thread
                            future.result()
                        except Exception as exc:
                            # Print errors to the tqdm bar
                            tqdm.write(str(exc))
                    
                    # Once all parallel tasks for this type are done, break to the next change type
                    break
    
    print("Synchronization complete.")

if __name__ == "__main__":
    main()
