import os
from pathlib import Path
import mmap
import time

def generate_super_fast(output_path, filename):
    full_path = Path(output_path) / filename
    total = 100_000_000
    chunk_size = 10_000_000  # 10M numbers per chunk
    entry_len = 9  # 8 digits + newline
    
    print(f"Ultra-Fast Generation of 100M 8-digit combos")
    print(f"Target file: {full_path}")
    
    try:
        start_time = time.time()
        
        # Pre-allocate file
        file_size = total * entry_len
        with open(full_path, 'wb') as f:
            f.seek(file_size - 1)
            f.write(b'\0')
        
        # Memory-map the file
        with open(full_path, 'r+b') as f:
            with mmap.mmap(f.fileno(), 0) as mm:
                # Generate in chunks
                for chunk_start in range(0, total, chunk_size):
                    chunk_end = min(chunk_start + chunk_size, total)
                    chunk_data = bytearray()
                    
                    # Generate chunk
                    for num in range(chunk_start, chunk_end):
                        # Format: 08d + newline (optimized)
                        chunk_data.extend(f"{num:08d}\n".encode('ascii'))
                    
                    # Write chunk
                    mm.seek(chunk_start * entry_len)
                    mm.write(chunk_data)
                    
                    # Progress
                    elapsed = time.time() - start_time
                    speed = (chunk_end / (elapsed + 1e-9)) / 1_000_000
                    print(f"\rProgress: {chunk_end/total:.1%} | Speed: {speed:.2f} M lines/sec", end="", flush=True)
        
        elapsed = time.time() - start_time
        print(f"\n Done in {elapsed:.2f} seconds ({total/elapsed:,.0f} lines/sec)")
    
    except Exception as e:
        print(f"\n Error: {e}")

# Settings
DEFAULT_OUTPUT_PATH = "."
DEFAULT_FILENAME = "num_pass_list.dict"

if __name__ == "__main__":
    generate_super_fast(DEFAULT_OUTPUT_PATH, DEFAULT_FILENAME)