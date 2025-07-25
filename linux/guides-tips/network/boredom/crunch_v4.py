import os
import sys
from pathlib import Path
import mmap
import time
import shutil
import numpy as np

# Fixed parameters
OUTPUT_DIRECTORY = "."                  # Output directory (current folder by default)
OUTPUT_FILENAME = "8digits-num.dict"    # Output file name
TOTAL_ENTRIES = 100_000_000             # Total combinations: 10^8 (00000000 to 99999999)
ENTRY_LENGTH = 9                        # 8 digits + \n (fixed length)
TEMP_SUFFIX = '.tmp'                    # Temporary file suffix
BUFFER_SIZE = 1_000_000                 # Buffer size for batch processing

def check_disk_space(path, required_bytes):
    """Verify free disk space with clear error messaging."""
    required_mb = required_bytes / (1024 * 1024)
    stat = shutil.disk_usage(path)
    free_mb = stat.free / (1024 * 1024)
    if free_mb < required_mb:
        raise IOError(
            f"Required: {required_mb:.1f} MB, Available: {free_mb:.1f} MB\n"
            f"Ensure at least {required_mb:.1f} MB of free space exists."
        )

def generate_full_8digit_combinations(output_dir):
    """Generate all 8-digit combinations (00000000 to 99999999)."""
    output_path = Path(output_dir) / OUTPUT_FILENAME
    temp_path = output_path.with_suffix(TEMP_SUFFIX)
    file_size = TOTAL_ENTRIES * ENTRY_LENGTH  # 900 MB

    print("[+] Generating all 8-digit combinations (00000000-99999999)...")
    print(f"[+] Output file: {output_path}")
    print(f"[+] Required space: {file_size / (1024**2):.1f} MB")

    try:
        # Check disk space before starting
        check_disk_space(output_dir, file_size)
        start_time = time.time()

        # Pre-allocate temporary file
        with open(temp_path, 'wb') as f:
            f.truncate(file_size)

        # Write data via memory-mapping with batch processing
        with open(temp_path, 'r+b') as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as mm:
                # Use numpy for efficient number formatting
                numbers = np.arange(0, TOTAL_ENTRIES, dtype=np.uint32)
                
                # Process in batches to balance memory usage and performance
                for i in range(0, TOTAL_ENTRIES, BUFFER_SIZE):
                    batch = numbers[i:i+BUFFER_SIZE]
                    # Format all numbers in the batch at once
                    formatted = np.char.zfill(batch.astype(str), 8) + '\n'
                    joined = ''.join(formatted)
                    
                    # Write the entire batch at once
                    mm.seek(i * ENTRY_LENGTH)
                    mm.write(joined.encode('ascii'))
                    
                    # Progress update
                    if i % (10 * BUFFER_SIZE) == 0 or i == TOTAL_ENTRIES - BUFFER_SIZE:
                        elapsed = time.time() - start_time
                        speed = i / max(elapsed, 1e-9) / 1_000_000
                        print(
                            f"\r[+] Progress: {i/TOTAL_ENTRIES:.1%} | "
                            f"Speed: {speed:.2f} million lines/sec",
                            end="", flush=True
                        )

        # Rename temp file to final name upon success
        temp_path.replace(output_path)
        elapsed = time.time() - start_time
        print(f"\n[+] Done! Time elapsed: {elapsed:.2f} sec.")
        print(f"[+] Average speed: {TOTAL_ENTRIES/elapsed/1_000_000:.2f} million lines/sec")

    except (KeyboardInterrupt, Exception) as e:
        # Cleanup on failure
        if temp_path.exists():
            print(f"\n[!] Deleting partial file...")
            temp_path.unlink()
        print(f"[!] Error: {type(e).__name__}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print()
    generate_full_8digit_combinations(OUTPUT_DIRECTORY)