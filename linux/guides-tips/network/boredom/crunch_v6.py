#!/usr/bin/env python3
import os
import sys
import signal
import logging
import threading
import queue
from pathlib import Path
import mmap
import time
import shutil
import numpy as np
from multiprocessing import Pool, cpu_count, Manager
import ctypes
from logging.handlers import QueueHandler, QueueListener

# ==================== Configuration ====================
OUTPUT_DIRECTORY = "./"
OUTPUT_FILENAME_BASE = "8digits-num"
OUTPUT_FILE_EXTENSION = ".dict"
OUTPUT_FILENAME = OUTPUT_FILENAME_BASE + OUTPUT_FILE_EXTENSION
TOTAL_ENTRIES = 100_000_000
ENTRY_LENGTH = 9  # 8 digits + newline
TEMP_SUFFIX = '.tmp'

# Resource control
MAX_WORKERS = 6
CHUNK_SIZE = 10_000_000
MEMORY_LIMIT_MB = 2048

# ==================== Logging Setup ====================
def setup_logging():
    """Configure multi-process logging with queue."""
    log_queue = queue.Queue(-1)  # No limit on queue size
    formatter = logging.Formatter(
        '%(asctime)s [%(processName)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler for debug logs
    file_handler = logging.FileHandler('crunch_debug.log', mode='w')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler for important messages
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Create and start listener
    listener = QueueListener(log_queue, file_handler, console_handler)
    listener.start()
    
    return log_queue, listener

# Initialize logging
log_queue, log_listener = setup_logging()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(QueueHandler(log_queue))

# ==================== Core Classes ====================
class ProcessController:
    """Manage process lifecycle and signal handling."""
    def __init__(self):
        self.shutdown_event = threading.Event()
        self.manager = None
        self.pool = None
        self._setup_signal_handlers()
        logger.debug("Process controller initialized")

    def _setup_signal_handlers(self):
        """Configure signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        logger.debug("Signal handlers configured")

    def _handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        signal_name = signal.Signals(signum).name
        logger.warning(f"Received {signal_name}, initiating shutdown...")
        self.shutdown_event.set()

# ==================== Utility Functions ====================
def ensure_directory_exists(path):
    """Ensure output directory exists with cross-platform support."""
    try:
        # Expand user paths (~) and environment variables
        expanded_path = os.path.expanduser(os.path.expandvars(path))
        path_obj = Path(expanded_path)
        
        if not path_obj.exists():
            logger.info(f"Creating directory: {expanded_path}")
            path_obj.mkdir(parents=True, exist_ok=True)
            logger.debug("Directory created successfully")
            
        return str(path_obj.resolve())
    except Exception as e:
        logger.error(f"Directory creation failed: {str(e)}", exc_info=True)
        raise

def check_disk_space(path, required_bytes):
    """Verify sufficient disk space is available."""
    try:
        # Ensure directory exists first
        validated_path = ensure_directory_exists(path)
        stat = shutil.disk_usage(validated_path)
        
        if stat.free < required_bytes:
            required_gb = required_bytes / (1024 ** 3)
            free_gb = stat.free / (1024 ** 3)
            error_msg = (f"Insufficient space. Need {required_gb:.1f}GB, "
                        f"have {free_gb:.1f}GB")
            logger.error(error_msg)
            raise IOError(error_msg)
            
        logger.debug(f"Disk check passed: {stat.free/(1024**3):.1f}GB available")
        return validated_path
    except Exception as e:
        logger.error(f"Disk space check failed: {str(e)}", exc_info=True)
        raise

def init_worker():
    """Initialize worker process settings."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    logger.debug(f"Worker {os.getpid()} initialized")

# ==================== Main Processing ====================
def generate_chunk(args):
    """Generate a chunk of number combinations."""
    start, end, shutdown_flag = args
    worker_logger = logging.getLogger(f"worker_{os.getpid()}")
    worker_logger.debug(f"Starting chunk {start}-{end}")
    
    if shutdown_flag.value:
        worker_logger.warning("Chunk aborted due to shutdown flag")
        return None
        
    try:
        numbers = np.arange(start, end, dtype=np.uint32)
        batch_size = min(100_000, end - start)
        result = bytearray()
        
        for i in range(0, len(numbers), batch_size):
            if shutdown_flag.value:
                worker_logger.warning("Batch processing interrupted by shutdown")
                return None
                
            batch = numbers[i:i+batch_size]
            formatted = np.char.zfill(batch.astype('U8'), 8) + '\n'
            result.extend(''.join(formatted).encode('ascii'))
        
        worker_logger.debug(f"Chunk {start}-{end} completed successfully")
        return bytes(result)
    except Exception as e:
        worker_logger.error(f"Chunk generation failed: {str(e)}", exc_info=True)
        return None

def generate_full_8digit_combinations(output_dir):
    """Main generation function with full error handling."""
    controller = ProcessController()
    file_size = TOTAL_ENTRIES * ENTRY_LENGTH
    
    try:
        # Validate and prepare directory
        validated_dir = check_disk_space(output_dir, file_size)
        output_path = Path(validated_dir) / OUTPUT_FILENAME
        temp_path = output_path.with_suffix(TEMP_SUFFIX)

        logger.info("=== Starting 8-Digit Combination Generator ===")
        logger.info(f"System cores: {cpu_count()}, Using workers: {MAX_WORKERS}")
        logger.info(f"Output file: {output_path}")
        logger.info(f"Total entries: {TOTAL_ENTRIES:,}")
        logger.info(f"Required space: {file_size/(1024**3):.2f} GB")

        # File preparation
        logger.debug("Pre-allocating output file")
        with open(temp_path, 'wb') as f:
            f.truncate(file_size)

        # Shared resources setup
        controller.manager = Manager()
        shutdown_flag = controller.manager.Value(ctypes.c_bool, False)
        logger.debug("Shared resources initialized")

        # Process pool setup
        logger.info(f"Starting {MAX_WORKERS} worker processes")
        controller.pool = Pool(
            MAX_WORKERS,
            init_worker,
            maxtasksperchild=100  # Prevent memory leaks
        )

        start_time = time.time()
        
        # Main processing loop
        with open(temp_path, 'r+b') as f, \
             mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as mm:
            
            chunks = [
                (i, min(i + CHUNK_SIZE, TOTAL_ENTRIES), shutdown_flag)
                for i in range(0, TOTAL_ENTRIES, CHUNK_SIZE)
            ]
            logger.info(f"Processing {len(chunks)} chunks")
            
            for i, result in enumerate(controller.pool.imap(generate_chunk, chunks)):
                if controller.shutdown_event.is_set():
                    logger.warning("Shutdown initiated, aborting processing")
                    shutdown_flag.value = True
                    raise KeyboardInterrupt()
                    
                if result is None:
                    logger.error("Critical chunk generation failure")
                    raise RuntimeError("Chunk generation failed")
                    
                # Write results
                start_pos = i * CHUNK_SIZE * ENTRY_LENGTH
                mm[start_pos:start_pos + len(result)] = result
                
                # Progress reporting
                if i % (max(1, len(chunks) // 10)) == 0 or i == len(chunks) - 1:
                    elapsed = time.time() - start_time
                    progress = (i + 1) / len(chunks)
                    remaining = (elapsed / progress) * (1 - progress) if progress > 0 else 0
                    logger.info(
                        f"Progress: {progress:.1%} | "
                        f"Elapsed: {time.strftime('%H:%M:%S', time.gmtime(elapsed))} | "
                        f"ETA: {time.strftime('%H:%M:%S', time.gmtime(remaining))}"
                    )

        # Finalization
        temp_path.replace(output_path)
        elapsed = time.time() - start_time
        logger.info(f"Successfully completed in {elapsed:.2f} seconds")
        logger.info(f"Output file created: {output_path}")
        return True

    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        return False
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}", exc_info=True)
        return False
    finally:
        # Cleanup in reverse order of initialization
        logger.info("Starting cleanup process")
        cleanup_resources(controller, temp_path)
        log_listener.stop()

def cleanup_resources(controller, temp_path):
    """Ensure all resources are properly released."""
    try:
        if controller.pool:
            logger.debug("Terminating worker pool")
            controller.pool.close()
            controller.pool.terminate()
            controller.pool.join()
            logger.debug("Worker pool terminated")
    except Exception as e:
        logger.error(f"Error terminating pool: {str(e)}", exc_info=True)

    try:
        if controller.manager:
            logger.debug("Shutting down manager")
            controller.manager.shutdown()
            logger.debug("Manager shut down")
    except Exception as e:
        logger.error(f"Error shutting down manager: {str(e)}", exc_info=True)

    try:
        if temp_path.exists():
            logger.debug(f"Removing temporary file: {temp_path}")
            temp_path.unlink(missing_ok=True)
            logger.debug("Temporary file removed")
    except Exception as e:
        logger.error(f"Error removing temp file: {str(e)}", exc_info=True)

    logger.info("Cleanup completed")

# ==================== Main Execution ====================
if __name__ == "__main__":
    try:
        print()
        print(f"Python {sys.version.split()[0]}")
        logger.info("Application started")
        
        success = generate_full_8digit_combinations(OUTPUT_DIRECTORY)
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.critical(f"Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Application shutdown complete")