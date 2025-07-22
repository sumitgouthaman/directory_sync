# Directory Sync

This script synchronizes two directories, a source and a destination, by copying, replacing, or deleting files and directories to make the destination a mirror of the source.

## Setup

This project uses `uv` for fast environment and package management.

1.  **Install `uv`:**
    Follow the instructions at [https://astral.sh/uv#installation](https://astral.sh/uv#installation) to install `uv`.

2.  **Create a virtual environment:**
    ```bash
    uv venv
    ```

3.  **Activate the virtual environment:**
    ```bash
    source .venv/bin/activate
    ```

4.  **Install the project in editable mode:**
    ```bash
    uv pip install -e .
    ```
    This will install the necessary dependencies and make the `directory-sync` command available in your shell.

## How to Run

There are two ways to run the tool:

### 1. Installing the Package

This method installs the `directory-sync` command in your virtual environment, allowing you to run it from any directory.

```bash
# After activating the virtual environment
uv pip install -e .
```

Once installed, you can run the tool as follows:

```bash
directory-sync --src /path/to/source --dest /path/to/destination
```

### 2. Running without Installation (Using `uv run`)

This method is useful for development or for running the script without adding it to your environment's installed packages. `uv` will use the entry point defined in `pyproject.toml`.

```bash
# After activating the virtual environment
uv run directory-sync --src /path/to/source --dest /path/to/destination
```

### Command-Line Arguments

-   `--src`: The path to the source directory.
-   `--dest`: The path to the destination directory.
-   `--compare_mode`: The method for comparing files. It can be either `size` (default) or `checksum`.
-   `--dry_run`: A flag that, if present, prevents the script from making any actual changes to the file system.

### Example Usage

To perform a dry run of a synchronization, comparing files by size:

```bash
uv run directory-sync -- --src /path/to/source --dest /path/to/destination --dry_run
```

To execute the synchronization, comparing files by checksum:

```bash
uv run directory-sync -- --src /path/to/source --dest /path/to/destination --compare_mode checksum
```

## Testing with Synthetic Data

For local development and testing, you can generate synthetic data to simulate a real-world synchronization scenario.

### Generating Test Data

The `generate_test_data.py` script creates two directories, `src` and `dest`, under `/tmp/test_data` (or a custom directory) with a random structure of files and subdirectories. These directories will have slight differences to test the synchronization logic.

#### Command-Line Arguments

-   `--max_depth`: Maximum depth of the directory structure.
-   `--approximate_files`: Approximate number of files to create.
-   `--approximate_size_of_each_file`: Approximate size of each file in bytes.
-   `--output_dir`: The base directory to generate the test data in (defaults to `/tmp/test_data`).

#### Example Usage

To generate a test set with a maximum depth of 4, around 100 files, and each file being approximately 2KB:

```bash
uv run python tests/generate_test_data.py --max_depth 4 --approximate_files 100 --approximate_size_of_each_file 2048
```

The script will output the paths to the generated `src` and `dest` directories.

### Running with Test Data

Once the test data is generated, you can use the output paths to run the tool:

```bash
uv run directory-sync -- --src /tmp/test_data/src --dest /tmp/test_data/dest --dry_run
```

This allows you to safely test the synchronization logic on a controlled set of data before using it on real directories.