#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2016, Perceptive Automation, LLC. All rights reserved.
# http://www.indigodomo.com

import indigo

import os
import sys
import time

import urllib2
import requests

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.

################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = False
		self.deviceList = []
		self.interval = None

	########################################
	def startup(self):
		self.debugLog(u"startup called")
		self.closedPrefsConfigUi(None, None)

	def shutdown(self):
		self.debugLog(u"shutdown called")

	########################################
	# deviceStartComm() is called on application launch for all of our plugin defined
	# devices, and it is called when a new device is created immediately after its
	# UI settings dialog has been validated. This is a good place to force any properties
	# we need the device to have, and to cleanup old properties.
	def deviceStartComm(self, dev):
		self.debugLog(u"deviceStartComm: %s" % (dev.name,))
		props = dev.pluginProps
		if dev.id not in self.deviceList:
			self.deviceList.append(dev.id)
			dev.stateListOrDisplayStateIdChanged()

	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		if not userCancelled:
			self.debugLog(u"[%s] Getting plugin preferences." % time.asctime())
			self.debugLog("The interval is " + self.pluginPrefs["interval"])

			try:		
				self.debug = self.pluginPrefs[u'showDebugInfo']
			except:
				self.debug = False

			try:
				if self.interval != self.pluginPrefs["interval"]:
					self.interval = self.pluginPrefs["interval"]
			except:
				indigo.server.log("[%s] Could not retrieve Polling Interval." % time.asctime())

	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		return (True, valuesDict)

	########################################
	# Relay / Dimmer Action callback
	######################
	def actionControlDevice(self, action, dev):
		###### TURN ON ######
		if action.deviceAction == indigo.kDeviceAction.TurnOn:
			url = u"http://" + dev.pluginProps["address"] + "/admin/api.php?enable&auth=" + dev.pluginProps["password"]
			response = requests.get(url)
			sendSuccess = True		# Set to False if it failed.

			if sendSuccess:
				# If success then log that the command was successfully sent.
				indigo.server.log(u"sent \"%s\" %s" % (dev.name, "on"))

				# And then tell the Indigo Server to update the state.
				dev.updateStateOnServer("onOffState", True)
			else:
				# Else log failure but do NOT update state on Indigo Server.
				indigo.server.log(u"send \"%s\" %s failed" % (dev.name, "on"), isError=True)

		###### TURN OFF ######
		elif action.deviceAction == indigo.kDeviceAction.TurnOff:
			url = u"http://" + dev.pluginProps["address"] + "/admin/api.php?disable&auth=" + dev.pluginProps["password"]
			response = requests.get(url)
			sendSuccess = True		# Set to False if it failed.

			if sendSuccess:
				# If success then log that the command was successfully sent.
				indigo.server.log(u"sent \"%s\" %s" % (dev.name, "off"))

				# And then tell the Indigo Server to update the state:
				dev.updateStateOnServer("onOffState", False)
			else:
				# Else log failure but do NOT update state on Indigo Server.
				indigo.server.log(u"send \"%s\" %s failed" % (dev.name, "off"), isError=True)

		###### TOGGLE ######
		elif action.deviceAction == indigo.kDeviceAction.Toggle:
			# Command hardware module (dev) to toggle here:
			newOnState = not dev.onState
			sendSuccess = True		# Set to False if it failed.

			if sendSuccess:
				# If success then log that the command was successfully sent.
				indigo.server.log(u"sent \"%s\" %s" % (dev.name, "toggle"))

				# And then tell the Indigo Server to update the state:
				dev.updateStateOnServer("onOffState", newOnState)
			else:
				# Else log failure but do NOT update state on Indigo Server.
				indigo.server.log(u"send \"%s\" %s failed" % (dev.name, "toggle"), isError=True)

	def udpateStatus(self, dev):
		self.debugLog(u"Sent \"%s\" %s" % (dev.name, "status request"))
		try:
			url = u"http://" + dev.pluginProps["address"] + "/admin/api.php?status&auth=" + dev.pluginProps["password"]
			r = requests.get(url)
			if "enabled" in r.text:
				self.debugLog(u"PiHole is Enabled")
				response = "on"
			elif "disabled" in r.text:
				self.debugLog(u"PiHole is Disabled")
				response = "off"
			dev.updateStateOnServer("onOffState", response)

		except ValueError:
			# The int() cast above might fail if the user didn't enter a number:
			indigo.server.log(u"Unable to update Pi Hole status")
			return

	########################################
	# General Action callback
	######################
	def actionControlUniversal(self, action, dev):

		###### STATUS REQUEST ######
		if action.deviceAction == indigo.kUniversalAction.RequestStatus:
			self.udpateStatus(dev)

	########################################
	def runConcurrentThread(self):
		self.debugLog("Starting concurrent thread")
		try:
			while True:
				for deviceId in self.deviceList:
					dev = indigo.devices[deviceId]
					self.udpateStatus(dev)
				self.sleep(int(self.interval))
		except self.StopThread:
			pass

	########################################