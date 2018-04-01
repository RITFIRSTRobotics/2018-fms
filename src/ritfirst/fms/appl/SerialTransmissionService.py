"""
A service that connects to the ASC and reads data

:author: Connor Henley, @thatging3rkid
"""
from threading import Thread

import sys

from core.utils.AllianceColor import AllianceColor
from core.utils.HeaderParser import HeaderParser
from ritfirst.fms.utils.SerialUtils import ser_readline


class SerialTransmissionService(Thread):
    cleanup = False

    def __init__(self, rser, bser, out_service, score_service):
        """
        Initialize the SerialTransmissionService

        :param rser: a PySerial object that has been initialized and is transmitting data for the Red alliance
        :param bser: a PySerial object that has been initialized and is transmitting data for the Blue alliance
        :param out_service: a data-structure to put the received data into
        :param score_service: a pointer to the ScoreService
        """
        Thread.__init__(self)

        self.rser = rser
        self.bser = bser
        self.out_service = out_service
        self.score_service = score_service

    def run(self):
        hp = HeaderParser("core/serial/usbser_constants.hpp")
        DELIMITER = hp.contents['DELIMITER']

        # Calculate the headers now to save processing time later
        calibrate_res_header = hp.contents['INIT_RESPONSE'].split(DELIMITER)[0]
        controller_data_header = hp.contents['CONTROLLER_DATA'].split(DELIMITER)[0]
        score_data_header = hp.contents['SCORE_DATA'].split(DELIMITER)[0]

        def _process(text, color):
            # Split it on the delimiter
            split = text.split(DELIMITER)

            if len(split) <= 1:
                print("SerialTransmissionService: unexpected transmission: `" + text + "`", file=sys.stderr)
                return

            # Compare the data header to the other headers
            if split[0] == calibrate_res_header:
                # ding calibration done
                print("SerialTransmissionService: calibration complete", file=sys.stderr)
            elif split[0] == controller_data_header:
                # Controller data sent, it needs to be pushed to the data-structure
                controller_num = int(split[1])
                controller_sticks = [None] * 4
                controller_sticks[0] = int(split[2])
                controller_sticks[1] = int(split[3])
                controller_sticks[2] = int(split[4])
                controller_sticks[3]= int(split[5])

                controller_buttons = [None] * 4


                # Need to clean up the number
                split[6] = split[6].strip()  # clean the '\n'
                try:
                    int(split[6])  # check the default input
                except ValueError:
                    try:
                        int(split[6][0:2])  # see if the first two characters are a valid int
                        split[6] = split[6][0:2]
                    except ValueError:
                        try:
                            int(split[6][0])  # if not, then it has to be only the first character
                            split[6] = split[6][0]
                        except:
                            split[6] = '15'
                # Decode the button data
                controller_buttons[0] = bool(int(split[6]) & 1)
                controller_buttons[1] = bool(int(split[6]) & 2)
                controller_buttons[2] = bool(int(split[6]) & 4)
                controller_buttons[3] = bool(int(split[6]) & 8)

                self.out_service.append(color, controller_num, controller_sticks, controller_buttons)

            elif split[0] == score_data_header:
                # A score happened
                self.score_service.scored(color, int(split[1]))
            else:
                # Unknown header
                print("SerialTransmissionService: unknown header `" + split[0] + "`", file=sys.stderr)

        while True:
            # Read and process data sent to the ASC
            if self.rser.in_waiting > 0:
                _process(ser_readline(self.rser), AllianceColor.RED)
            if self.bser.in_waiting > 0:
                _process(ser_readline(self.bser), AllianceColor.BLUE)

            # Check for cleanup
            if self.cleanup:
                break

        # Close the serial connection
        self.rser.close()
        self.bser.close()


