import os
import sys
from pathlib import Path
import mmap
import time
import shutil
import numpy as np
from multiprocessing import Pool, cpu_count, shared_memory

# Configuration - Adjusted for memory safety
OUTPUT_DIRECTORY = "./"
OUTPUT_FILENAME = "8digits-num.dict"
TOTAL_ENTRIES = 100_000_000
ENTRY_LENGTH = 9
TEMP_SUFFIX = '.tmp'
CHUNK_SIZE = 2_000_000  # Reduced chunk size for memory safety
NUM_WORKERS = min(cpu_count() - 4, 4)  # Limit workers to 4 for memory

def check_disk_space(path, required_bytes):
    """Verify free disk space."""
    stat = shutil.disk_usage(path)
    if stat.free < required_bytes:
        required_gb = required_bytes / (1024 ** 3)
        free_gb = stat.free / (1024 ** 3)
        raise IOError(f"Insufficient space. Need {required_gb:.1f}GB, have {free_gb:.1f}GB")

def generate_chunk(args):
    """Generate a chunk of numbers and return as bytes."""
    start, end = args
    numbers = np.arange(start, end, dtype=np.uint32)
    # Memory-efficient formatting in batches
    batch_size = 100_000
    result = bytearray()
    for i in range(0, len(numbers), batch_size):
        batch = numbers[i:i+batch_size]
        formatted = np.char.zfill(batch.astype('U8'), 8) + '\n'
        result.extend(''.join(formatted).encode('ascii'))
    return bytes(result)

def generate_full_8digit_combinations(output_dir):
    """Generate all 8-digit combinations with memory-safe parallel processing."""
    output_path = Path(output_dir) / OUTPUT_FILENAME
    temp_path = output_path.with_suffix(TEMP_SUFFIX)
    file_size = TOTAL_ENTRIES * ENTRY_LENGTH
    
    print(f"[+] Generating {TOTAL_ENTRIES:,} combinations (00000000-99999999)")
    print(f"[+] Output: {output_path}")
    print(f"[+] Workers: {NUM_WORKERS}, Chunk size: {CHUNK_SIZE:,}")
    print(f"[+] Required space: {file_size / (1024**3):.2f} GB")

    try:
        check_disk_space(output_dir, file_size)
        start_time = time.time()

        # Pre-allocate file
        with open(temp_path, 'wb') as f:
            f.truncate(file_size)

        # Process in parallel with memory limits
        with open(temp_path, 'r+b') as f, \
             mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as mm, \
             Pool(NUM_WORKERS, maxtasksperchild=10) as pool:
            
            chunks = [(i, min(i + CHUNK_SIZE, TOTAL_ENTRIES)) 
                     for i in range(0, TOTAL_ENTRIES, CHUNK_SIZE)]
            
            for i, result in enumerate(pool.imap(generate_chunk, chunks)):
                start_pos = i * CHUNK_SIZE * ENTRY_LENGTH
                mm[start_pos:start_pos + len(result)] = result
                
                # Progress update
                if i % max(1, len(chunks) // 10) == 0 or i == len(chunks) - 1:
                    elapsed = time.time() - start_time
                    progress = (i + 1) / len(chunks)
                    remaining = (elapsed / progress) * (1 - progress) if progress > 0 else 0
                    print(
                        f"\r[+] {progress:.1%} | "
                        f"Elapsed: {elapsed:.1f}s | "
                        f"ETA: {remaining:.1f}s | "
                        f"Mem: {sys.getsizeof(result)/1024/1024:.1f}MB/chunk",
                        end='', flush=True
                    )

        # Finalize
        temp_path.replace(output_path)
        elapsed = time.time() - start_time
        speed = TOTAL_ENTRIES / elapsed / 1_000_000
        print(f"\n[+] Done in {elapsed:.2f} seconds ({speed:.2f} million entries/sec)")

    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        print(f"\n[!] Failed: {type(e).__name__}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print()
    generate_full_8digit_combinations(OUTPUT_DIRECTORY)