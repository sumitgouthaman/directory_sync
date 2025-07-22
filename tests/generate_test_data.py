import argparse
import os
import random
import string
import shutil

def generate_random_string(length):
    """Generate a random string of fixed length."""
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

def create_random_file(path, size):
    """Create a file with random content."""
    with open(path, 'w') as f:
        f.write(generate_random_string(size))

def create_dir_structure(base_dir, max_depth, current_depth, all_dirs):
    """Recursively create a directory structure."""
    if current_depth >= max_depth:
        return

    for _ in range(random.randint(1, 3)):
        dir_name = generate_random_string(8)
        dir_path = os.path.join(base_dir, dir_name)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            all_dirs.append(dir_path)
            create_dir_structure(dir_path, max_depth, current_depth + 1, all_dirs)

def generate_test_data(base_dir, max_depth, approximate_files, approximate_size_of_each_file):
    """Generate test data in the specified directory."""
    src_dir = os.path.join(base_dir, 'src')
    dest_dir = os.path.join(base_dir, 'dest')

    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    
    os.makedirs(src_dir)
    os.makedirs(dest_dir)

    # 1. Create directory structure in src
    all_dirs = [src_dir]
    create_dir_structure(src_dir, max_depth, 0, all_dirs)

    # 2. Create files and place them randomly in the created directories
    for _ in range(approximate_files):
        target_dir = random.choice(all_dirs)
        file_name = generate_random_string(10) + ".txt"
        file_path = os.path.join(target_dir, file_name)
        create_random_file(file_path, approximate_size_of_each_file)

    # 3. Create a similar but slightly different structure in dest
    copy_and_modify_structure(src_dir, dest_dir)

def copy_and_modify_structure(src, dest):
    """Copy the structure from src to dest and introduce some changes."""
    for item in os.listdir(src):
        src_path = os.path.join(src, item)
        dest_path = os.path.join(dest, item)

        if os.path.isdir(src_path):
            # Randomly decide to skip creating some directories in dest
            if random.random() > 0.1:
                os.makedirs(dest_path, exist_ok=True)
                copy_and_modify_structure(src_path, dest_path)
        elif os.path.isfile(src_path):
            # Randomly decide to copy, modify or skip files
            rand = random.random()
            if rand < 0.7: # copy as is
                shutil.copy2(src_path, dest_path)
            elif rand < 0.9: # copy and modify
                 shutil.copy2(src_path, dest_path)
                 with open(dest_path, 'a') as f_dest:
                    f_dest.write("modified")
            # else: # skip creating the file in dest, which means it will be a "to be created" case for sync

    # Add some files in dest that are not in src (to be deleted)
    if random.random() < 0.8:
        file_name = generate_random_string(10) + "_extra.txt"
        file_path = os.path.join(dest, file_name)
        create_random_file(file_path, 100)

def main():
    parser = argparse.ArgumentParser(description="Generate test data for directory synchronization.")
    parser.add_argument('--max_depth', type=int, default=3, help='Maximum depth of the directory structure.')
    parser.add_argument('--approximate_files', type=int, default=20, help='Approximate number of files to create.')
    parser.add_argument('--approximate_size_of_each_file', type=int, default=1024, help='Approximate size of each file in bytes.')
    parser.add_argument('--output_dir', type=str, default='/tmp/test_data', help='The base directory to generate the test data in.')

    args = parser.parse_args()

    generate_test_data(args.output_dir, args.max_depth, args.approximate_files, args.approximate_size_of_each_file)
    print(f"Test data generated in {args.output_dir}")
    print(f"Source: {os.path.join(args.output_dir, 'src')}")
    print(f"Destination: {os.path.join(args.output_dir, 'dest')}")

if __name__ == "__main__":
    main()