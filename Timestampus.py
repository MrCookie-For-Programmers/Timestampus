import pyautogui
import datetime
import time
import keyboard
import sys
import re
import pyperclip # Import pyperclip

# --- Configuration ---
TRIGGER_PHRASE_START = "timestampus"
# Regex to match the full pattern: "timestampus DD.MM.YYYY HH:MM FLAG"
# 'R' is now re-added to the accepted flags.
TRIGGER_PATTERN_REGEX = r"timestampus (\d{2}\.\d{2}\.\d{4}) (\d{2}:\d{2}) ([tdDFfFR])"

# Adjust this delay if characters are missed or typed too fast
TYPE_DELAY = 0.01
# Maximum characters to consider for buffering. This should be larger than any expected command.
MAX_INPUT_LENGTH_TO_PROCESS = 60 # Increased buffer significantly for safety

# Platform-specific hotkeys
if sys.platform == 'darwin': # macOS
    SELECT_ALL_HOTKEY = ['command', 'a']
    PASTE_HOTKEY = ['command', 'v']
    DELETE_KEY = 'backspace' # On macOS, 'delete' key is typically 'backspace'
else: # Windows/Linux
    SELECT_ALL_HOTKEY = ['ctrl', 'a']
    PASTE_HOTKEY = ['ctrl', 'v']
    DELETE_KEY = 'backspace' # Or 'delete' depending on desired behavior. 'backspace' is common for deleting selected text.

def get_discord_timestamp(date_str, time_str, flag):
    """
    Converts DD.MM.YYYY HH:MM and a flag into a Discord timestamp.
    """
    try:
        # Parse date and time
        day, month, year = map(int, date_str.split('.'))
        hour, minute = map(int, time_str.split(':'))

        # Create a datetime object
        dt_object = datetime.datetime(year, month, day, hour, minute)

        # Convert to Unix timestamp (seconds since epoch)
        unix_timestamp = int(dt_object.timestamp())

        # Validate flag - 'R' is now explicitly included
        valid_flags = ['t', 'T', 'd', 'D', 'f', 'F', 'R']
        if flag not in valid_flags:
            print(f"Warning: Invalid flag '{flag}'. Using 'f' as default.")
            flag = 'f' # Default to 'f' if flag is genuinely invalid.

        return f"<t:{unix_timestamp}:{flag}>"
    except ValueError:
        print("Error: Invalid date or time format. Please use DD.MM.YYYY HH:MM.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during timestamp generation: {e}")
        return None

def perform_replacement(matched_text, date_part, time_part, flag_part):
    """
    Simulates clearing the line (Ctrl+A + Backspace), copies to clipboard, and pastes.
    `matched_text` is the exact string that was detected.
    """
    discord_timestamp = get_discord_timestamp(date_part, time_part, flag_part)

    if discord_timestamp:
        print(f"Generated timestamp: {discord_timestamp}")

        # Store current clipboard content to restore it later
        original_clipboard_content = None
        try:
            original_clipboard_content = pyperclip.paste()
        except pyperclip.PyperclipException:
            print("Could not access clipboard to save original content (might be empty or restricted).")

        # Crucial pause to allow the last typed character to register in the application
        # and cursor to be stable before selecting and deleting.
        time.sleep(0.1) # Increased pause for more stability

        # Select all text in the current input field
        print("Attempting to select all text...")
        pyautogui.hotkey(*SELECT_ALL_HOTKEY, _pause=TYPE_DELAY)
        
        # Delete the selected text
        print("Attempting to delete selected text...")
        pyautogui.press(DELETE_KEY, _pause=TYPE_DELAY)

        # Copy the new timestamp to the clipboard
        pyperclip.copy(discord_timestamp)
        print("Timestamp copied to clipboard. Attempting to paste...")

        # Paste the timestamp using Ctrl+V (or Command+V on macOS)
        pyautogui.hotkey(*PASTE_HOTKEY, _pause=TYPE_DELAY)
        
        # Optional: Restore original clipboard content after a short delay
        # This is good practice but might interfere with very fast subsequent operations.
        # time.sleep(0.1) 
        # if original_clipboard_content is not None:
        #     pyperclip.copy(original_clipboard_content)
        #     print("Original clipboard content restored.")

        print("Replacement attempt finished.")
    else:
        print("Failed to generate timestamp. Keeping original input (or attempting to restore).")

# --- Keyboard listener setup ---
current_line_buffer = ""
processing_input = False

def on_key_event(event):
    global current_line_buffer, processing_input

    if event.event_type == keyboard.KEY_DOWN:
        # Ignore modifier keys and other special keys
        if event.name in ['shift', 'alt', 'ctrl', 'tab', 'caps lock', 'esc', 'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12', 'home', 'end', 'page up', 'page down', 'insert', 'delete', 'left arrow', 'right arrow', 'up arrow', 'down arrow', 'left windows', 'right windows', 'alt gr', 'fn', 'prt sc', 'scroll lock', 'pause break', 'num lock', 'print screen', 'context menu']:
            return

        if processing_input:
            # If we are in the middle of processing a replacement, ignore new input
            return

        if event.name == 'backspace':
            if current_line_buffer:
                current_line_buffer = current_line_buffer[:-1]
        elif event.name == 'space':
            current_line_buffer += ' '
        elif event.name == 'enter':
            # Reset buffer on enter, as the "hotkey" should have fired already
            current_line_buffer = ""
            return
        elif event.name and len(event.name) == 1: # Regular character
            current_line_buffer += event.name
        elif event.name and event.name.isdigit(): # Numpad digits might come as '1', '2' etc.
             current_line_buffer += event.name


        # Keep buffer to a reasonable length to avoid excessive memory usage
        # This also acts as a rough "start of line" filter
        if len(current_line_buffer) > MAX_INPUT_LENGTH_TO_PROCESS:
            current_line_buffer = current_line_buffer[-MAX_INPUT_LENGTH_TO_PROCESS:]


        # Check for the pattern immediately after each character is typed
        lower_buffer = current_line_buffer.lower()
        
        # Use re.search for more flexible matching (e.g., if there's leading text before the trigger)
        match = re.search(TRIGGER_PATTERN_REGEX, lower_buffer)
        
        if match:
            # Crucial check: Ensure the detected pattern is at the very end of the current buffer.
            # This prevents accidental triggers if "timestampus" appears mid-sentence.
            if lower_buffer.endswith(match.group(0)):
                processing_input = True # Set flag to prevent re-entry
                print(f"Pattern detected: '{match.group(0)}'")
                
                # Extract the parts for timestamp generation
                date_part = match.group(1)
                time_part = match.group(2)
                flag_part = match.group(3)
                
                # The exact string that matched the regex
                matched_full_text = match.group(0)

                # Perform the replacement
                perform_replacement(matched_full_text, date_part, time_part, flag_part)
                
                # Reset buffer after successful processing
                current_line_buffer = ""
                processing_input = False # Reset flag

# Hook the keyboard listener
print(f"Listening for pattern: '{TRIGGER_PATTERN_REGEX}'...")
print("Type 'timestampus DD.MM.YYYY HH:MM [t, T, d, D, f, F, or R]' and it will attempt to replace it.")
print("The script will try to clear the current line using Ctrl+A + Backspace before pasting.")
print("Press Ctrl+C in this terminal to stop the script.")
print("Also, If you want relative time you have to type T instead of R, then replace the last character with r manually (for some reason the normal method is broken)")
print("you can now minimize the window. have fun!")

try:
    keyboard.hook(on_key_event)
    keyboard.wait() # Keep the script running
except KeyboardInterrupt:
    print("\nScript stopped by user.")
except Exception as e:
    print(f"An error occurred: {e}")
    print("Ensure you have installed pyperclip, pyautogui, and keyboard (pip install pyperclip pyautogui keyboard).")
    print("On Linux, you might need to run with sudo: sudo python your_script_name.py")
    print("On Windows, try running your command prompt/powershell as Administrator.")
finally:
    keyboard.unhook_all()
    sys.exit()