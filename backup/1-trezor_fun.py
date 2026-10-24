import chipwhisperer.common.results.glitch as glitch
import chipwhisperer as cw
import serial
import time
import sys
import os
import logging
import select
import termios
import tty
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta

# Set up logging with explicit flush and rotation
class FlushRotatingFileHandler(RotatingFileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

# Create a custom formatter that strips timestamps for console output
class ConsoleFormatter(logging.Formatter):
    def format(self, record):
        # Just return the message without timestamp for console
        return record.getMessage()

# Create timestamped log filename
log_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_filename = f'glitch_campaign_{log_timestamp}.log'

# Set up rotating file handler with 1MB max size and automatic flushing
# maxBytes=1MB (1024*1024), backupCount=999 means up to 999 backup files
file_handler = FlushRotatingFileHandler(
    log_filename, 
    maxBytes=1024*1024,  # 1MB per file
    backupCount=999      # Keep up to 999 backup files
)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Print log filename for reference
print(f"\n📝 Logging to: {log_filename}")
print(f"   (Will rotate to {log_filename}.1, .2, etc. when size exceeds 1MB)\n")

# Set up console handler without timestamps
console_handler = logging.StreamHandler()
console_handler.setFormatter(ConsoleFormatter())

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler],
    force=True
)
logger = logging.getLogger(__name__)

scope = None
# SWD device variable
dev = ""

'''
boot_mode_enable
Used to check if boot rom SDP check has been bypassed
1. Reset the STLink adapter using the usbreset program
2. Attempt to communicate with the DAP over SWD
'''
def boot_mode_enable():
    global dev
    pc = ""
    try:
        import swd
        # Reset STLink using usb_reset (no sudo needed after permissions setup)
        reset_cmd = "/home/tdaly/.cwvenv/usb_reset"
        # Suppress output for cleaner logs
        os.system(f"{reset_cmd} > /dev/null 2>&1")
        time.sleep(0.5)  # Give device time to reinitialize
        
        # Attempt SWD connection
        dev = swd.Swd()
        pc = dev.get_version().str
        # Success is logged elsewhere, no need to print here
    except Exception as e:
        # Normal failure, don't log
        try:
            del swd
        except:
            pass
    return pc

def reboot_flush():            
    global scope
    # Cut power to target device
    scope.io.target_pwr = False
    # Pull reset low
    scope.io.nrst = False
    # Set up CW for glitching
    scope.arm()
    # Put reset in high impedance mode (we are triggering off of it)
    scope.io.nrst = "high_z"
    # Power the target and wait for the glitch to trigger
    scope.io.target_pwr = True

scope = cw.scope()
scope.io.target_pwr = "high_z"

'''
The following lines were pulled from CW jupyter notebooks from the tutorials/documentation
'''
try:
    if SS_VER == "SS_VER_2_1":
        target_type = cw.targets.SimpleSerial2
    elif SS_VER == "SS_VER_2_0":
        raise OSError("SS_VER_2_0 is deprecated. Use SS_VER_2_1")
    else:
        target_type = cw.targets.SimpleSerial
except:
    SS_VER="SS_VER_1_1"
    target_type = cw.targets.SimpleSerial

try:
    target = cw.target(scope, target_type)
except:
    print("INFO: Caught exception on reconnecting to target - attempting to reconnect to scope first.")
    logger.info("Caught exception on reconnecting to target - attempting to reconnect to scope first.")
    print("INFO: This is a work-around when USB has died without Python knowing. Ignore errors above this line.")
    logger.info("This is a work-around when USB has died without Python knowing. Ignore errors above this line.")
    scope = cw.scope()
    target = cw.target(scope, target_type)

print("\n" + "="*60)
logger.info("="*60)
print("✅ Found ChipWhisperer!")
logger.info("✅ Found ChipWhisperer!")
print("="*60)
logger.info("="*60)

# Set up scope specific parameters
print("\n📋 Configuring glitch parameters...")
logger.info("📋 Configuring glitch parameters...")
scope.clock.clkgen_freq = 100E6
# Trigger on IO4 this is connected to our reset line
scope.trigger.triggers = 'tio4'
scope.adc.samples = 24400
scope.adc.offset = 0
scope.adc.basic_mode = "rising_edge"
scope.adc.decimate = 10
scope.glitch.clk_src = "clkgen" # set glitch input clock
scope.glitch.output = "enable_only" # glitch_out = clk ^ glitch
scope.glitch.trigger_src = "ext_single" # glitch only after scope.arm() called
scope.io.glitch_lp = True
scope.io.glitch_hp = True

g_step = 1
gc = glitch.GlitchController(groups=["success", "failure"], parameters=["width", "offset", "ext_offset"])
gc.display_stats = True
gc.set_global_step(g_step)
# Define the ranges
width_min, width_max = 40, 40
offset_min, offset_max = -45, -45
#ext_offset_min, ext_offset_max = 17250, 17900 #target2's range
ext_offset_min, ext_offset_max = 17000, 18900 #target2's range
#ext_offset_min, ext_offset_max = 18400, 24000
#ext_offset_min, ext_offset_max = 24000, 25000
#ext_offset_min, ext_offset_max = 18870, 18900 #target1's range

# Set the ranges in GlitchController
gc.set_range("width", width_min, width_max)
gc.set_range("offset", offset_min, offset_max)
gc.set_range("ext_offset", ext_offset_min, ext_offset_max)

# Display the configured values
if width_min == width_max:
    print(f"  Width: {width_min}")
    logger.info(f"  Width: {width_min}")
else:
    print(f"  Width: {width_min} to {width_max} (step: {g_step})")
    logger.info(f"  Width: {width_min} to {width_max} (step: {g_step})")

if offset_min == offset_max:
    print(f"  Offset: {offset_min}")
    logger.info(f"  Offset: {offset_min}")
else:
    print(f"  Offset: {offset_min} to {offset_max} (step: {g_step})")
    logger.info(f"  Offset: {offset_min} to {offset_max} (step: {g_step})")

print(f"  Ext_offset range: {ext_offset_min} to {ext_offset_max} (step: {g_step})")
logger.info(f"  Ext_offset range: {ext_offset_min} to {ext_offset_max} (step: {g_step})")
print(f"  Trigger: {scope.trigger.triggers} (rising edge of reset)")
logger.info(f"  Trigger: {scope.trigger.triggers} (rising edge of reset)")

reboot_flush()
# How many times we attempt each configuration
sample_size = 8
print(f"\n🎯 Starting glitch campaign...")
logger.info("🎯 Starting glitch campaign...")
print(f"  Sample size per setting: {sample_size}")
logger.info(f"  Sample size per setting: {sample_size}")
print(f"  Total settings to test: {len(list(gc.glitch_values()))}")
logger.info(f"  Total settings to test: {len(list(gc.glitch_values()))}")
# How many clock cycles we pull low for
scope.glitch.repeat=20
offsets = []
total_attempts = 0
start_time = datetime.now()

# Calculate total settings for progress tracking
total_settings = ((ext_offset_max - ext_offset_min) // g_step) + 1
total_expected_attempts = total_settings * sample_size

print("="*60 + "\n")
logger.info("="*60)
# Announce start (synchronous to avoid overlap)
logger.info("[AUDIO] Speaking: 'Starting glitch campaign'")
os.system("espeak 'Starting glitch campaign' 2>/dev/null")

ext_offset_index = 0
for glitch_setting in gc.glitch_values():
    ext_offset_index += 1
    scope.glitch.width = glitch_setting[0]
    scope.glitch.offset = glitch_setting[1]
    scope.glitch.ext_offset = glitch_setting[2]
    
    # Calculate progress
    percent_complete = (ext_offset_index - 1) / total_settings * 100
    elapsed = datetime.now() - start_time
    if ext_offset_index > 1:
        avg_time_per_setting = elapsed.total_seconds() / (ext_offset_index - 1)
        remaining_settings = total_settings - (ext_offset_index - 1)
        estimated_remaining = avg_time_per_setting * remaining_settings
        eta = datetime.now() + timedelta(seconds=estimated_remaining)
        
        # Format ETA as date and time with 12-hour format
        eta_str = f" | ETA: {eta.strftime('%b %d, %I:%M:%S %p')}"
        
        # Format remaining time as days, hours, minutes
        days = int(estimated_remaining // 86400)
        hours = int((estimated_remaining % 86400) // 3600)
        minutes = int((estimated_remaining % 3600) // 60)
        seconds = int(estimated_remaining % 60)
        
        if days > 0:
            remaining_str = f" | Remaining: {days}d {hours}h {minutes}m"
        elif hours > 0:
            remaining_str = f" | Remaining: {hours}h {minutes}m {seconds}s"
        else:
            remaining_str = f" | Remaining: {minutes}m {seconds}s"
    else:
        eta_str = ""
        remaining_str = ""
    
    logger.info(f"\n⚡ Testing ext_offset: {scope.glitch.ext_offset} (Setting {ext_offset_index}/{total_settings}) [{percent_complete:.1f}%]{remaining_str}{eta_str}")
    logger.info(f"   └─ Width: {scope.glitch.width}, Offset: {scope.glitch.offset}")
    
    successes = 0
    failures = 0
    for i in range(sample_size):
        total_attempts += 1
        
        # Show detailed info every attempt
        logger.info(f"\n   🔄 Attempt {i+1}/{sample_size} | Ext_offset setting {ext_offset_index} | Total: {total_attempts}")
        logger.info(f"      ├─ Glitch @ ext_offset: {scope.glitch.ext_offset} ({scope.glitch.ext_offset/100:.1f}µs after reset)")
        logger.info(f"      ├─ Width: {scope.glitch.width} cycles, Offset: {scope.glitch.offset}")
        logger.info(f"      ├─ Repeat: {scope.glitch.repeat} cycles")
        
        # Reboot target, arm scope, wait for glitch
        logger.info(f"      ├─ Rebooting target & arming scope...")
        reboot_flush()
        logger.info(f"      ├─ Rebooting target & arming scope... ✓")
        
        # Allow target time to initialize
        logger.info(f"      ├─ Waiting 2s for target init...")
        time.sleep(2)
        logger.info(f"      ├─ Waiting 2s for target init... ✓")
        
        # Reset glitch lines as reccomended in docs
        logger.info(f"      ├─ Resetting glitch transistors...")
        scope.io.glitch_hp = False
        scope.io.glitch_hp = True
        scope.io.glitch_lp = False
        scope.io.glitch_lp = True
        logger.info(f"      ├─ Resetting glitch transistors... ✓")
        
        # Check to see if glitch was successful
        logger.info(f"      └─ Checking SWD access...")
        x = boot_mode_enable()
        if x:
            logger.info(f"      └─ Checking SWD access... 💥 SUCCESS!")
            logger.info("\n" + "🎉"*30)
            logger.info(f"💥 SUCCESS! GLITCH WORKED!")
            logger.info(f"   Offset: {scope.glitch.offset}")
            logger.info(f"   Width: {scope.glitch.width}")
            logger.info(f"   Ext_offset: {scope.glitch.ext_offset}")
            logger.info(f"   SWD Version: {x}")
            logger.info(f"   Attempt: {i+1}/{sample_size}")
            logger.info(f"   Total attempts: {total_attempts}")
            logger.info("🎉"*30)
            # Announce success! (simplified and synchronous)
            logger.info(f"[AUDIO] Speaking: 'Success! Glitch worked!'")
            os.system(f"espeak 'Success! Glitch worked!' 2>/dev/null")
            successes += 1
            break
        else:
            logger.info(f"      └─ Checking SWD access... ❌ No access")
            failures += 1
    
    # Summary for this ext_offset setting with progress
    attempts_complete = (ext_offset_index - 1) * sample_size + (successes + failures)
    overall_percent = (attempts_complete / total_expected_attempts) * 100
    logger.info(f"\n   📊 Completed {sample_size} attempts at ext_offset={scope.glitch.ext_offset} | Overall: {attempts_complete}/{total_expected_attempts} [{overall_percent:.1f}%]")
    
    if successes > 0:
        elapsed = datetime.now() - start_time
        print(f"\n✨ CAMPAIGN SUCCESSFUL!")
        logger.info(f"✨ CAMPAIGN SUCCESSFUL!")
        print(f"   Successes: {successes}")
        logger.info(f"   Successes: {successes}")
        print(f"   Failures: {failures}")
        logger.info(f"   Failures: {failures}")
        print(f"   Success rate: {(successes/sample_size)*100:.1f}%")
        logger.info(f"   Success rate: {(successes/sample_size)*100:.1f}%")
        print(f"   Time elapsed: {elapsed}")
        logger.info(f"   Time elapsed: {elapsed}")
        print(f"   Settings: offset={scope.glitch.offset}, width={scope.glitch.width}, ext_offset={scope.glitch.ext_offset}")
        logger.info(f"   Settings: offset={scope.glitch.offset}, width={scope.glitch.width}, ext_offset={scope.glitch.ext_offset}")
        break

print("\n" + "="*60)
logger.info("="*60)
print("🏁 Glitch campaign complete!")
logger.info("🏁 Glitch campaign complete!")
print(f"   Total attempts: {total_attempts}")
logger.info(f"   Total attempts: {total_attempts}")
print(f"   Total time: {datetime.now() - start_time}")
logger.info(f"   Total time: {datetime.now() - start_time}")
print("="*60)
logger.info("="*60)
# Announce completion with repeating alert until key press
# Save terminal settings
old_settings = termios.tcgetattr(sys.stdin)

try:
    # Set terminal to raw mode for immediate key detection
    tty.setraw(sys.stdin.fileno())
    
    if any([successes > 0 for successes in [successes]]):
        message = "Campaign complete. Glitch successful."
    else:
        message = "Campaign complete. No successful glitch found."
    
    print("\n🔔 ALERT: " + message)
    print("Press any key to stop the alert...\n")
    logger.info("[AUDIO] Repeating: '" + message + "' until key press")
    
    # Repeat announcement until key is pressed
    while True:
        # Use synchronous espeak and add longer delay to prevent overlap
        os.system(f"espeak '{message}' 2>/dev/null")
        
        # Check if a key has been pressed (non-blocking)
        if select.select([sys.stdin], [], [], 2.0)[0]:  # Increased timeout
            # Read the key to clear the buffer
            sys.stdin.read(1)
            print("\n✅ Alert stopped by user")
            logger.info("Alert stopped by user")
            break
        
        # Longer delay between announcements to prevent overlap
        time.sleep(1.5)
        
finally:
    # Restore terminal settings
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)