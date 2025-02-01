import os
import csv
import argparse
import subprocess
import sys
from pathlib import Path
import re  # Add this at the top with other imports
import io
import datetime

# Ensure Unicode output works in Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# List of required packages
REQUIRED_PACKAGES = ['mutagen']

def check_dependencies():
    """Check if required packages are installed, install if missing"""
    import importlib.util
    missing_packages = []
    
    for package in REQUIRED_PACKAGES:
        spec = importlib.util.find_spec(package)
        if spec is None:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Missing packages: {', '.join(missing_packages)}")
        print("Attempting to install missing packages...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
            print("Packages installed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install packages: {e}")
            print("Please install the required packages manually:")
            print(f"pip install {' '.join(REQUIRED_PACKAGES)}")
            exit(1)

# Check dependencies before proceeding
check_dependencies()

# Now we can safely import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.wave import WAVE
import struct

# Add these color constants at the top of the file
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def detect_delimiter(file_path):
    """Detect if file is CSV or TSV based on first line"""
    with open(file_path, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        if '\t' in first_line:
            return '\t'
        return ','

def validate_file_structure(file_path, delimiter):
    """Validate the file has at least 3 columns"""
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=delimiter)
        try:
            first_row = next(reader)
            if len(first_row) < 3:
                return False, "File must have at least 3 columns"
            return True, None
        except StopIteration:
            return False, "File is empty"

def load_expected_tags(file_path, debug_print):
    """Load expected tags from CSV/TSV file"""
    try:
        delimiter = detect_delimiter(file_path)
        valid, error = validate_file_structure(file_path, delimiter)
        if not valid:
            raise ValueError(error)

        expected_tags = {}
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile, delimiter=delimiter)
            
            for row in reader:
                # Skip comments and empty lines
                if not row or row[0].startswith('#'):
                    continue
                    
                if len(row) >= 3:
                    tag = row[0].strip()
                    description = row[1].strip('() *')  # Remove parentheses, asterisks
                    pattern = row[2].strip()
                    
                    # Handle special characters in pattern
                    pattern = pattern.strip()
                    # Replace • with comma in regex patterns
                    if any(c in pattern for c in '[]*?+'):
                        pattern = pattern.replace('•', ',')
                    
                    # Handle TXXX tags specially
                    if tag == 'TXXX':
                        # Get the specific TXXX tag type from description
                        # Remove any trailing characters like ) or **
                        txxx_type = description.rstrip(')*')
                        tag = f'TXXX:{txxx_type}'
                    else:
                        # Remove ** markers from other tag names
                        tag = tag.strip('*')
                    
                    debug_print(f"Debug: Reading tag: {tag} ({description}), pattern: {pattern}")
                    expected_tags[tag] = {
                        'description': description,
                        'pattern': pattern,
                        'is_regex': any(c in pattern for c in '[]*?+')
                    }
        
        if not expected_tags:
            raise ValueError("No valid tags found in the file")
        return expected_tags
    except UnicodeDecodeError as e:
        raise ValueError(f"Unicode error reading tags file: {str(e)}. Make sure the file is saved with UTF-8 encoding.")
    except Exception as e:
        raise ValueError(f"Error reading tags file: {str(e)}")

def get_tag_mapping():
    """Return a mapping of friendly names to ID3 tag names"""
    return {
        'album': 'TALB',
        'composer': 'TCOM',
        'artist': 'TPE1',
        'albumartist': 'TPE2',
        'genre': 'TCON',
        'date': 'TYER',
        'title': 'TIT2',
        'copyright': 'TCOP',
        'grouping': 'TIT1',
        'version': 'TIT3',
        'comment': 'COMM',
        'description': 'desc',
        'publisher': 'TPUB',
        'releasetime': 'TDRL',
        'series': 'TXXX:SERIES',
        'series-part': 'TXXX:SERIES-PART',
        'tmp_genre1': 'TXXX:TMP_GENRE1',
        'tracknumber': 'TRCK'  # Added this mapping
    }

def get_wav_tags(wav_file):
    """Extract tags from WAV file INFO chunk"""
    tags = {}
    try:
        if hasattr(wav_file, 'tags'):
            for key, value in wav_file.tags.items():
                # Convert from bytes if needed
                if isinstance(value, bytes):
                    try:
                        tags[key] = value.decode('utf-8')
                    except UnicodeDecodeError:
                        tags[key] = value.decode('latin-1')
                else:
                    tags[key] = str(value)
        
        # Try to get ID3 tags if present
        if hasattr(wav_file, 'tags') and hasattr(wav_file.tags, '_EasyID3__id3'):
            id3 = wav_file.tags._EasyID3__id3
            for key in id3.keys():
                if key not in tags:
                    tags[key] = str(id3[key])
        
        return tags
    except Exception as e:
        print(f"Debug: Error reading WAV tags: {str(e)}")
        return {}

def get_wav_tag_mapping():
    """Return a mapping of WAV INFO tags to ID3 tag names"""
    return {
        'INAM': 'TIT2',  # Title
        'IART': 'TPE1',  # Artist
        'IPRD': 'TALB',  # Album
        'ICMT': 'COMM',  # Comments
        'ICRD': 'TYER',  # Date created
        'IGNR': 'TCON',  # Genre
        'ICOP': 'TCOP',  # Copyright
        'IENG': 'TCOM',  # Engineer (we'll use for composer)
        'ISBJ': 'TIT1',  # Subject (we'll use for content group)
        'ITCH': 'TPE2'   # Technician (we'll use for album artist)
    }

def verify_tags(file_path, expected_tags, debug_print):
    try:
        tag_mapping = get_tag_mapping()
        
        if file_path.endswith('.mp3'):
            audio = EasyID3(file_path)
            raw_id3 = audio._EasyID3__id3 if hasattr(audio, '_EasyID3__id3') else None
            
            # Debug all available tags
            debug_print(f"\nDebug: Available tags in {os.path.basename(file_path)}:")
            try:
                # First show standard tags
                for key in audio.keys():
                    try:
                        value = audio[key][0] if audio[key] else ''
                        debug_print(f"  {key}: {value}")
                        if key in tag_mapping:
                            debug_print(f"    (ID3: {tag_mapping[key]})")
                    except UnicodeEncodeError:
                        debug_print(f"  {key}: <contains special characters>")
                
                # Then explicitly check TXXX tags
                if raw_id3:
                    debug_print("\nDebug: Available TXXX tags:")
                    for key in raw_id3.keys():
                        if key.startswith('TXXX:'):
                            try:
                                value = str(raw_id3[key].text[0])
                                debug_print(f"  {key}: {value}")
                            except Exception as e:
                                debug_print(f"  {key}: <error reading value: {e}>")
            except Exception as e:
                debug_print(f"  Warning: Could not display some tags: {str(e)}")

            # Process MP3 tags
            results = {}
            for tag, tag_info in expected_tags.items():
                actual_value = ''
                
                # Try to get the value in different ways depending on the tag type
                if tag in ['TDRL', 'TPUB', 'MVNM', 'MVIN']:
                    # These tags are stored as TXXX tags
                    if raw_id3:
                        txxx_key = f'TXXX:{tag}'
                        if txxx_key in raw_id3:
                            actual_value = str(raw_id3[txxx_key].text[0])
                
                elif tag == 'COMM':
                    if raw_id3:
                        # Look for any COMM frame regardless of language code
                        comm_frames = [k for k in raw_id3.keys() if k.startswith('COMM')]
                        if comm_frames:
                            debug_print(f"Debug: Found raw COMM frames: {comm_frames}")
                            # Try to get the first available COMM frame
                            for comm_key in comm_frames:
                                try:
                                    frame = raw_id3[comm_key]
                                    debug_print(f"Debug: Raw COMM frame data: {frame}")
                                    # Access the text directly from the frame
                                    if hasattr(frame, 'text'):
                                        actual_value = str(frame.text[0])
                                        debug_print(f"Debug: Using {comm_key} text: {actual_value}")
                                        break
                                    elif hasattr(frame, '_text'):
                                        actual_value = str(frame._text[0])
                                        debug_print(f"Debug: Using {comm_key} _text: {actual_value}")
                                        break
                                    elif hasattr(frame, 'value'):
                                        actual_value = str(frame.value)
                                        debug_print(f"Debug: Using {comm_key} value: {actual_value}")
                                        break
                                except Exception as e:
                                    debug_print(f"Debug: Error reading COMM frame {comm_key}: {e}")
                                    debug_print(f"Debug: Frame attributes: {dir(frame)}")
                        else:
                            debug_print("Debug: No COMM frames found in raw ID3 tags")
                            debug_print(f"Debug: Available raw ID3 frames: {list(raw_id3.keys())}")
                
                elif tag == 'DESC':
                    if raw_id3:
                        # First try TXXX:DESC
                        if 'TXXX:DESC' in raw_id3:
                            actual_value = str(raw_id3['TXXX:DESC'].text[0])
                            debug_print(f"Debug: Using TXXX:DESC for description: {actual_value}")
                        # Optionally fall back to COMM if no DESC found
                        elif not actual_value:
                            debug_print("Debug: No TXXX:DESC found, checking for alternative description tags")
                            for key in raw_id3.keys():
                                if key.startswith('TXXX:') and 'DESC' in key.upper():
                                    actual_value = str(raw_id3[key].text[0])
                                    debug_print(f"Debug: Found alternative description in {key}: {actual_value}")
                                    break
                
                elif tag.startswith('TXXX:'):
                    if raw_id3:
                        # Get the specific part after TXXX:
                        txxx_type = tag.split(':', 1)[1]
                        # Try different TXXX formats
                        possible_keys = [
                            f'TXXX:{txxx_type}',
                            f'TXXX:TXXX ({txxx_type})',
                            f'TXXX:TXX ({txxx_type})**',
                            f'TXXX:TXXX ({txxx_type})**',
                            # Try case-insensitive variants
                            f'TXXX:TXXX ({txxx_type.lower()})**',
                            f'TXXX:TXXX ({txxx_type.title()})**',
                            f'TXXX:TXX ({txxx_type.upper()})**'
                        ]
                        debug_print(f"Debug: Checking TXXX keys for {tag}: {possible_keys}")
                        for key in possible_keys:
                            if key in raw_id3:
                                actual_value = str(raw_id3[key].text[0])
                                debug_print(f"Debug: Found value using key {key}: {actual_value}")
                                break
                            # Also try without the TXXX: prefix in the comparison
                            stripped_key = key.replace('TXXX:', '')
                            if stripped_key in raw_id3:
                                actual_value = str(raw_id3[stripped_key].text[0])
                                debug_print(f"Debug: Found value using stripped key {stripped_key}: {actual_value}")
                                break
                
                else:
                    # Standard tag handling
                    if tag in audio:
                        actual_value = audio[tag][0]
                    else:
                        # Try friendly name
                        friendly_name = next((k for k, v in tag_mapping.items() if v == tag), None)
                        if friendly_name and friendly_name in audio:
                            actual_value = audio[friendly_name][0]

                # Process the result
                if actual_value:
                    if tag_info['is_regex']:
                        matches = re.match(f"^{tag_info['pattern']}$", actual_value)
                        results[tag] = {
                            'expected': tag_info['pattern'],
                            'actual': actual_value,
                            'match': bool(matches),
                            'is_pattern': True
                        }
                    else:
                        results[tag] = {
                            'expected': tag_info['pattern'],
                            'actual': actual_value,
                            'match': actual_value == tag_info['pattern'],
                            'is_pattern': False
                        }
                else:
                    results[tag] = {
                        'expected': tag_info['pattern'],
                        'actual': '',
                        'match': False,
                        'is_pattern': tag_info['is_regex']
                    }

            return results

        elif file_path.endswith('.wav'):
            audio = WAVE(file_path)
            wav_tags = get_wav_tags(audio)
            
            debug_print(f"\nDebug: Available tags in {os.path.basename(file_path)}:")
            for key, value in wav_tags.items():
                try:
                    debug_print(f"  {key}: {value}")
                    if key in wav_mapping:
                        debug_print(f"    (ID3 equivalent: {wav_mapping[key]})")
                except UnicodeEncodeError:
                    debug_print(f"  {key}: <contains special characters>")
            
            results = {}
            for tag, tag_info in expected_tags.items():
                # Check both WAV and ID3 style tags
                wav_key = next((k for k, v in wav_mapping.items() if v == tag), None)
                actual_value = wav_tags.get(tag, '') or wav_tags.get(wav_key, '')
                
                if actual_value:
                    if tag_info['is_regex']:
                        matches = re.match(f"^{tag_info['pattern']}$", actual_value)
                        results[tag] = {
                            'expected': tag_info['pattern'],
                            'actual': actual_value,
                            'match': bool(matches),
                            'is_pattern': True
                        }
                    else:
                        results[tag] = {
                            'expected': tag_info['pattern'],
                            'actual': actual_value,
                            'match': actual_value == tag_info['pattern'],
                            'is_pattern': False
                        }
                else:
                    debug_print(f"Debug: Tag '{tag}' ({tag_info['description']}) not found in WAV file")
                    if wav_key:
                        debug_print(f"Debug: Also checked WAV tag '{wav_key}'")
                    results[tag] = {
                        'expected': tag_info['pattern'],
                        'actual': '',
                        'match': False,
                        'is_pattern': tag_info['is_regex']
                    }
            return results
        else:
            return {'error': "Unsupported file format"}
    except Exception as e:
        debug_print(f"Debug: Error processing {file_path}: {str(e)}")
        return {'error': str(e)}

def process_directory(directory, expected_tags, debug_print):
    results = {}
    wav_count = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.wav'):
                wav_count += 1
            elif file.endswith('.mp3'):
                file_path = Path(root) / file
                result = verify_tags(str(file_path), expected_tags, debug_print)
                results[str(file_path)] = result
    
    if wav_count > 0:
        print(f"\n{wav_count} WAV files skipped (disabled)")
    return results

def get_file_path(prompt):
    while True:
        path = input(prompt).strip()
        if os.path.isfile(path):
            return path
        print(f"Error: File '{path}' not found. Please try again.")

def print_output(message, output_file=None, color=True):
    """Print message to console and optionally to file (without color codes)"""
    # Print to console with colors
    print(message)
    
    # Print to file without color codes if output file is specified
    if output_file:
        # Remove color codes for file output
        clean_message = re.sub(r'\033\[[0-9;]*m', '', message)
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(clean_message + '\n')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Verify ID3 tags in MP3 files')
    parser.add_argument('-t', '--tag-file', required=True,
                        help='Path to CSV/TSV file containing expected tags')
    parser.add_argument('-f', '--folder', required=True,
                        help='Path to folder containing audio files to check')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show detailed debug output (useful if you get unexpected results)')
    parser.add_argument('-o', '--output-file', action='store_true',
                        help='Save results to a plaintext file, in the source audio folder')
    args = parser.parse_args()

    # Create a debug print function that only prints in verbose mode
    def debug_print(*print_args, **print_kwargs):
        if args.verbose:
            print(*print_args, **print_kwargs)

    debug_print("\nDebug: Command line arguments received:")
    debug_print(f"  Tag file: {args.tag_file}")
    debug_print(f"  Folder: {args.folder}")
    debug_print()

    # Create output file path if needed
    output_file = None
    if args.output_file:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(args.folder, f"check-id3_results_{timestamp}.txt")

    try:
        if args.tag_file:
            csv_path = args.tag_file
        else:
            csv_path = get_file_path(
                "Enter path to CSV/TSV file containing expected tags: "
            )
        
        expected_tags = load_expected_tags(csv_path, debug_print)
        print(f"Successfully loaded {len(expected_tags)} expected tags from '{csv_path}'")
        
        directory = args.folder
        if not os.path.isdir(directory):
            print(f"Error: Directory '{directory}' not found.")
            exit(1)
        
        print("\nProcessing files...")
        results = process_directory(directory, expected_tags, debug_print)
        
        # Initialize statistics
        stats = {
            'total_files': 0,
            'files_with_errors': 0,
            'files_passed': 0,
            'files_with_missing_tags': 0,
            'files_with_incorrect_tags': 0,
            'total_tags_checked': 0,
            'tags_matched': 0,
            'tags_mismatched': 0,
            'tags_missing': 0
        }
        
        print_output("\nVerification Results:", output_file)
        for file, result in results.items():
            mismatches_found = False
            file_mismatches = []
            
            # Increment total files counter for each file processed
            stats['total_files'] += 1
            
            if 'error' in result:
                print_output(f"\nFile: {Colors.CYAN}{os.path.basename(file)}{Colors.END}", output_file)
                print_output(f"{Colors.RED}[-]{Colors.END} Error: {result['error']}", output_file)
                stats['files_with_errors'] += 1
            else:
                file_has_missing_tags = False
                file_has_incorrect_tags = False
                file_all_tags_match = True
                
                # First collect all mismatches
                for tag, values in result.items():
                    stats['total_tags_checked'] += 1
                    if values['actual'] == '':
                        stats['tags_missing'] += 1
                        file_has_missing_tags = True
                        mismatches_found = True
                        file_mismatches.append(
                            f"{Colors.RED}[-]{Colors.END} {Colors.BOLD}{tag}{Colors.END}: "
                            f"{Colors.YELLOW}<not found>{Colors.END}"
                        )
                    elif not values['match']:
                        stats['tags_mismatched'] += 1
                        file_has_incorrect_tags = True
                        file_all_tags_match = False
                        mismatches_found = True
                        pattern_type = f"({Colors.BLUE}pattern{Colors.END})" if values.get('is_pattern') else ""
                        file_mismatches.append(
                            f"{Colors.RED}[-]{Colors.END} {Colors.BOLD}{tag}{Colors.END}: "
                            f"Expected {pattern_type} '{Colors.GREEN}{values['expected']}{Colors.END}', "
                            f"Found '{Colors.RED}{values['actual']}{Colors.END}'"
                        )
                    else:
                        stats['tags_matched'] += 1
                
                # Only print file name and mismatches if there are any
                if mismatches_found:
                    print_output(f"\nFile: {Colors.CYAN}{os.path.basename(file)}{Colors.END}", output_file)
                    for mismatch in file_mismatches:
                        print_output(mismatch, output_file)
                
                if file_has_missing_tags:
                    stats['files_with_missing_tags'] += 1
                if file_has_incorrect_tags:
                    stats['files_with_incorrect_tags'] += 1
                if file_all_tags_match and not file_has_missing_tags:
                    stats['files_passed'] += 1

        # Print summary with colors
        print_output(f"\n{Colors.BOLD}========== Summary =========={Colors.END}", output_file)
        print_output(f"Files Processed: {Colors.CYAN}{stats['total_files']}{Colors.END}", output_file)
        print_output(f"Files Passed: {Colors.GREEN}{stats['files_passed']}{Colors.END}", output_file)
        print_output(f"Files with Errors: {Colors.RED}{stats['files_with_errors']}{Colors.END}", output_file)
        print_output(f"Files with Missing Tags: {Colors.YELLOW}{stats['files_with_missing_tags']}{Colors.END}", output_file)
        print_output(f"Files with Incorrect Tags: {Colors.RED}{stats['files_with_incorrect_tags']}{Colors.END}", output_file)
        print_output(f"\n{Colors.BOLD}Tag Statistics:{Colors.END}", output_file)
        print_output(f"Total Tags Checked: {Colors.CYAN}{stats['total_tags_checked']}{Colors.END}", output_file)
        print_output(f"Tags Matched: {Colors.GREEN}{stats['tags_matched']}{Colors.END}", output_file)
        print_output(f"Tags Mismatched: {Colors.RED}{stats['tags_mismatched']}{Colors.END}", output_file)
        print_output(f"Tags Missing: {Colors.YELLOW}{stats['tags_missing']}{Colors.END}", output_file)
        print_output(f"{Colors.BOLD}==========================={Colors.END}", output_file)
    
        if output_file:
            print(f"\nResults have been saved to: {output_file}")
    
    except Exception as e:
        print_output(f"\nError: {str(e)}", output_file)
        print_output("Please check your input file and try again.", output_file)
        exit(1) 