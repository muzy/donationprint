#!/usr/bin/python
import os
import sys
import syslog 
import usb.core
import usb.util
import daemon

with daemon.DaemonContext():

	VENDOR_ID = 0x0801
	PRODUCT_ID = 0x0002
	DATA_SIZE = 337


	syslog.syslog("Starting application.")

	device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
	if device is None:
		syslog.syslog(syslog.LOG_ERR, "Could not find MagTek USB HID Swipe Reader.")
		sys.exit("Could not find MagTek USB HID Swipe Reader.")


	if device.is_kernel_driver_active(0):
		try:
			device.detach_kernel_driver(0)
		except usb.core.USBError as e:
			syslog.syslog(syslog.LOG_ERR, "Could not detach kernel driver: %s" % str(e))
			sys.exit("Could not detatch kernel driver: %s" % str(e))

	try:
		device.set_configuration()
		device.reset()
	except usb.core.USBError as e:
		syslog.syslog(syslog.LOG_ERR, "Could not set configuration: %s" % str(e))
		sys.exit("Could not set configuration: %s" % str(e))
		
	endpoint = device[0][(0,0)][0]

	data = []
	swiped = False
	syslog.syslog("Ready. Awaiting card!")

	def printform(account,bank):
		filepath = sys.path[0]
		os.system("sed -e 's/##account##/%s/g' -e 's/##bank##/%s/g' %s/bon.svg | inkscape --without-gui --export-ps=/dev/stdout /dev/stdin | lp -d Star_TSP143_" % (account, bank, filepath))

	def printthanks():
		filepath = sys.path[0]
		os.system("lp -d Star_TSP143_ -o media=om_x72-mmy50-mm_71.96x49.74mm %s/danke.ps" % str(filepath))

	while 1:
		try:
			data += device.read(endpoint.bEndpointAddress, endpoint.wMaxPacketSize)
			swiped = True
			if len(data) >= DATA_SIZE:
				newdata = "".join(map(chr, data))
				account = newdata[241:251]
				bank = newdata[232:240]
				if account.isdigit() and bank.isdigit():
					syslog.syslog("Got working card. Printing form.")
					printform(account,bank)
					printthanks()
				else:
					syslog.syslog(syslog.LOG_ERR, "Unreadable card. Printing blank bon.")
					printform(" "," ")
					printthanks()
				swiped = False
				data = []

		except usb.core.USBError as e:
			if e.args == ('Operation timed out',) and swiped:
				if len(data) < DATA_SIZE:
					syslog.syslog(syslog.LOG_ERR, "Bad swipe. (%d bytes)" % len(data))
					data = []
					swiped = False
					continue
				else:
					syslog.syslog(syslog.LOG_ERR, "Not enough data grabbed. (%d bytes)" % len(data))
					data = []
					swiped = False
					continue
		
