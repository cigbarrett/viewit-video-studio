
import os
import time
import shutil
import glob
from datetime import datetime, timedelta
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cleanup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_file_age_hours(file_path):
    try:
        file_mtime = os.path.getmtime(file_path)
        current_time = time.time()
        age_seconds = current_time - file_mtime
        age_hours = age_seconds / 3600
        return age_hours
    except OSError as e:
        logger.error(f"Error getting file age for {file_path}: {e}")
        return 0

def safe_remove_file(file_path):
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
            logger.info(f"Removed file: {file_path}")
            return True
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)
            logger.info(f"Removed directory: {file_path}")
            return True
    except OSError as e:
        logger.error(f"Error removing {file_path}: {e}")
        return False
    return False

def cleanup_temp_directory(temp_dir="temp", max_age_hours=6):
    if not os.path.exists(temp_dir):
        logger.warning(f"Temp directory {temp_dir} does not exist")
        return 0
    
    removed_count = 0
    logger.info(f"Cleaning up temp directory: {temp_dir}")
    
    for item in os.listdir(temp_dir):
        item_path = os.path.join(temp_dir, item)
        
        try:
            age_hours = get_file_age_hours(item_path)
            
            if age_hours > max_age_hours:
                if item.startswith('proj_') and os.path.isdir(item_path):
                    if safe_remove_file(item_path):
                        removed_count += 1
                        logger.info(f"Removed old project directory: {item} (age: {age_hours:.1f}h)")
                
                
                elif item.startswith('music_') and item.endswith('.mp3'):
                    if safe_remove_file(item_path):
                        removed_count += 1
                        logger.info(f"Removed old music file: {item} (age: {age_hours:.1f}h)")
                

                elif item.startswith('temp_frame_') and item.endswith('.jpg'):
                    if safe_remove_file(item_path):
                        removed_count += 1
                        logger.info(f"Removed old frame file: {item} (age: {age_hours:.1f}h)")
                
                elif os.path.isfile(item_path) and not item.endswith(('.py', '.log', '.txt')):
                    if safe_remove_file(item_path):
                        removed_count += 1
                        logger.info(f"Removed old temp file: {item} (age: {age_hours:.1f}h)")
        
        except Exception as e:
            logger.error(f"Error processing {item_path}: {e}")
    
    return removed_count

def cleanup_uploads_directory(uploads_dir="uploads", max_age_hours=6):
    if not os.path.exists(uploads_dir):
        logger.warning(f"Uploads directory {uploads_dir} does not exist")
        return 0
    
    removed_count = 0
    logger.info(f"Cleaning up uploads directory: {uploads_dir}")
    
    for item in os.listdir(uploads_dir):
        item_path = os.path.join(uploads_dir, item)
        
        try:
            if item.startswith('proj_') and os.path.isdir(item_path):
                age_hours = get_file_age_hours(item_path)
                
                if age_hours > max_age_hours:
                    if safe_remove_file(item_path):
                        removed_count += 1
                        logger.info(f"Removed old upload project: {item} (age: {age_hours:.1f}h)")
        
        except Exception as e:
            logger.error(f"Error processing upload {item_path}: {e}")
    
    return removed_count

def cleanup_archive_directory(archive_dir="archive", max_age_hours=6):
    if not os.path.exists(archive_dir):
        logger.warning(f"Archive directory {archive_dir} does not exist")
        return 0
    
    removed_count = 0
    logger.info(f"Cleaning up archive directory: {archive_dir}")
    
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
    
    for item in os.listdir(archive_dir):
        item_path = os.path.join(archive_dir, item)
        
        try:
            if os.path.isfile(item_path):
                _, ext = os.path.splitext(item.lower())
                if ext in video_extensions:
                    age_hours = get_file_age_hours(item_path)
                    
                    if age_hours > max_age_hours:
                        if safe_remove_file(item_path):
                            removed_count += 1
                            logger.info(f"Removed old archive video: {item} (age: {age_hours:.1f}h)")
        
        except Exception as e:
            logger.error(f"Error processing archive file {item_path}: {e}")
    
    return removed_count

def cleanup_outputs_directory(outputs_dir="outputs", max_age_hours=6):
    if not os.path.exists(outputs_dir):
        logger.warning(f"Outputs directory {outputs_dir} does not exist")
        return 0
    
    removed_count = 0
    logger.info(f"Cleaning up outputs directory: {outputs_dir}")
    
    for item in os.listdir(outputs_dir):
        item_path = os.path.join(outputs_dir, item)
        
        try:
            age_hours = get_file_age_hours(item_path)
            
            if age_hours > max_age_hours:
                if safe_remove_file(item_path):
                    removed_count += 1
                    logger.info(f"Removed old output file: {item} (age: {age_hours:.1f}h)")
        
        except Exception as e:
            logger.error(f"Error processing output file {item_path}: {e}")
    
    return removed_count

def get_directory_size(directory):
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except OSError:
                    pass
    except OSError:
        pass
    return total_size

def format_bytes(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

def run_cleanup(max_age_hours=6, dry_run=False):
    logger.info(f"{'DRY RUN: ' if dry_run else ''}Starting cleanup of files older than {max_age_hours} hours")
    
    directories = ["temp", "uploads", "archive", "outputs"]
    initial_sizes = {}
    for directory in directories:
        if os.path.exists(directory):
            initial_sizes[directory] = get_directory_size(directory)
    
    total_removed = 0
    
    if not dry_run:
        total_removed += cleanup_temp_directory(max_age_hours=max_age_hours)
        total_removed += cleanup_uploads_directory(max_age_hours=max_age_hours)
        total_removed += cleanup_archive_directory(max_age_hours=max_age_hours)
        total_removed += cleanup_outputs_directory(max_age_hours=max_age_hours)
    else:
        logger.info("DRY RUN: Would cleanup the following directories...")
        for directory in directories:
            if os.path.exists(directory):
                logger.info(f"  {directory}/")
    
    if not dry_run:
        total_space_freed = 0
        for directory in directories:
            if directory in initial_sizes and os.path.exists(directory):
                final_size = get_directory_size(directory)
                space_freed = initial_sizes[directory] - final_size
                total_space_freed += space_freed
                logger.info(f"{directory}: {format_bytes(space_freed)} freed")
        
        logger.info(f"Cleanup completed. Removed {total_removed} items, freed {format_bytes(total_space_freed)}")
    else:
        logger.info("DRY RUN completed. Use run_cleanup(dry_run=False) to actually remove files.")
    
    return total_removed

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up old AI Video Editor files')
    parser.add_argument('--hours', type=float, default=6.0, 
                        help='Maximum age in hours (default: 6)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be deleted without actually deleting')
    
    args = parser.parse_args()
    
    try:
        removed_count = run_cleanup(max_age_hours=args.hours, dry_run=args.dry_run)
        print(f"Cleanup completed successfully. {'Would remove' if args.dry_run else 'Removed'} {removed_count} items.")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        print(f"Cleanup failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
