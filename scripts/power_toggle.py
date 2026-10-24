import time, chipwhisperer as cw

scope = cw.scope()

print("[*] Power OFF")
scope.io.target_pwr = False
time.sleep(2)

print("[*] Power ON")
scope.io.target_pwr = True
time.sleep(2)

scope.dis()

