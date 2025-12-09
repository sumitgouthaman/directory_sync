# Directory Sync

This script synchronizes two directories, a source and a destination, by copying, replacing, or deleting files and directories to make the destination a mirror of the source.

## Setup

This project uses `uv` for easy execution and dependency management.

1.  **Install `uv`:**
    Follow the instructions at [https://astral.sh/uv#installation](https://astral.sh/uv#installation) to install `uv`.

## How to Run

You can run the script directly using `uv run`. `uv` will automatically install the necessary dependencies defined in `pyproject.toml`.

```bash
uv run directory-sync --src /path/to/source --dest /path/to/destination
```

### Command-Line Arguments

-   `--src`: The path to the source directory.
-   `--dest`: The path to the destination directory.
-   `--compare_mode`: The method for comparing files. It can be either `size` (default) or `checksum`.
-   `--dry_run`: A flag that, if present, prevents the script from making any actual changes to the file system.
-   `--workers`: Number of parallel threads to use (defaults to CPU count).

### Interactive Mode

The script runs in an interactive mode by default:
-   `y`: Synchronize the current file.
-   `n`: Skip the current file.
-   `t`: **Trust** mode. Switches to parallel execution for **all remaining files** without further prompts.

### Example Usage

To perform a dry run of a synchronization, comparing files by size:

```bash
uv run directory-sync --src /path/to/source --dest /path/to/destination --dry_run
```

To execute the synchronization, comparing files by checksum:

```bash
uv run directory-sync --src /path/to/source --dest /path/to/destination --compare_mode checksum
```

## Testing with Synthetic Data

For local development and testing, you can generate synthetic data to simulate a real-world synchronization scenario.

### Generating Test Data

The `generate_test_data.py` script creates two directories, `src` and `dest`, under `/tmp/test_data` (or a custom directory) with a random structure of files and subdirectories.

### Example Usage

To generate a test set with a maximum depth of 4, around 100 files, and each file being approximately 2KB:

```bash
uv run -m tests.generate_test_data --max_depth 4 --approximate_files 100 --approximate_size_of_each_file 2048
```
*Note: We use `-m` and the module path because the test script is inside a package structure, or you can run it by path if you set PYTHONPATH.*
Alternatively, running by path:
```bash
uv run tests/generate_test_data.py --max_depth 4 --approximate_files 100 --approximate_size_of_each_file 2048
```

The script will output the paths to the generated `src` and `dest` directories.

### Running with Test Data

Once the test data is generated, you can use the output paths to run the tool:

```bash
uv run directory-sync --src /tmp/test_data/src --dest /tmp/test_data/dest --dry_run
```