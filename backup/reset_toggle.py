import chipwhisperer as cw
import time

scope = cw.scope()

# Device is already powered on, just do a reset
print("Device already ON - performing reset...")

# Pull reset low while device is running
scope.io.nrst = False
print("Reset pulled LOW")
time.sleep(1)  # Hold reset for 500ms

# Release reset to let MCU restart (rising edge)
scope.io.nrst = True
print("Reset released HIGH - MCU restarting")
time.sleep(1)

scope.dis()
print("Reset complete.")
