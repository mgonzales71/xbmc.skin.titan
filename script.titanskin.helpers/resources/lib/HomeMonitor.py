#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
import threading
import xbmcvfs
import random
import xml.etree.ElementTree as etree
import base64
import time

import Utils as utils


class HomeMonitor(threading.Thread):
    
    event = None
    exit = False
    delayedTaskInterval = 899
    lastWeatherNotificationCheck = None
    lastNextAiredNotificationCheck = None
    win = None
    
    def __init__(self, *args):
        utils.logMsg("HomeMonitor - started")
        self.win = xbmcgui.Window( 10000 )
        self.event =  threading.Event()
        threading.Thread.__init__(self, *args)   
        
    
    def stop(self):
        utils.logMsg("HomeMonitor - stop called")
        self.exit = True
        self.event.set()

    def run(self):
        
        listItem = None
        lastListItem = None
        mainMenuContainer = "300"

        while (xbmc.abortRequested == False and self.exit != True):
            
            #do some background stuff every 15 minutes
            if (xbmc.getCondVisibility("!Window.IsActive(fullscreenvideo)")):
                if (self.delayedTaskInterval >= 900):
                    self.updatePlexlinks()
                    self.checkNotifications()
                    self.delayedTaskInterval = 0
            
            # monitor main menu when home is active
            if (xbmc.getCondVisibility("Window.IsActive(home) + !Window.IsActive(fullscreenvideo)")):

                #monitor widget window prop
                if self.win.getProperty("ShowWidget") == "show" and not xbmc.getCondVisibility("Window.IsActive(selectdialog) | Window.IsActive(shutdownmenu) | Window.IsActive(contextmenu)"):
                    self.showWidget()
                
                listItem = xbmc.getInfoLabel("Container(%s).ListItem.Label" %mainMenuContainer)
                if ((listItem != lastListItem) and xbmc.getCondVisibility("!Container(%s).Scrolling" %mainMenuContainer)):
                    
                    # update the widget content
                    if (xbmc.getCondVisibility("!Skin.HasSetting(DisableAllWidgets) + !Skin.String(GadgetRows, 3)")):
                        
                        #spotlight widget
                        if xbmc.getCondVisibility("Skin.String(GadgetRows, enhanced)"):
                            self.setSpotlightWidget(mainMenuContainer)
                        
                        #normal widget
                        self.setWidget(mainMenuContainer)

                    lastListItem = listItem
  
                else:
                    xbmc.sleep(150)
                    self.delayedTaskInterval += 0.15

            else:
                lastListItem = None
                xbmc.sleep(1000)
                self.delayedTaskInterval += 1
                
    
    
    def showWidget(self):
        linkCount = 20
        while linkCount != 0 and not xbmc.getCondVisibility("ControlGroup(77777).HasFocus"):
            xbmc.executebuiltin('Control.SetFocus(77777,0)')
            linkCount -= 1
            xbmc.sleep(50)
    
    def updatePlexlinks(self):
        
        if xbmc.getCondVisibility("System.HasAddon(plugin.video.plexbmc)"): 
            utils.logMsg("update plexlinks started...")
            
            #initialize plex window props by using the amberskin entrypoint for now
            if not self.win.getProperty("plexbmc.0.title"):
                xbmc.executebuiltin('RunScript(plugin.video.plexbmc,amberskin)')
                #wait for max 20 seconds untill the plex nodes are available
                count = 0
                while (count < 80 and self.win.getProperty("plexbmc.0.title") == ""):
                    xbmc.sleep(250)
                    count += 1
            
            #fallback to normal skin init
            if not self.win.getProperty("plexbmc.0.title"):
                xbmc.executebuiltin('RunScript(plugin.video.plexbmc,skin)')
                count = 0
                while (count < 80 and self.win.getProperty("plexbmc.0.title") == ""):
                    xbmc.sleep(250)
                    count += 1
            
            #get the plex setting if there are subnodes
            plexaddon = xbmcaddon.Addon(id='plugin.video.plexbmc')
            hasSecondayMenus = plexaddon.getSetting("secondary") == "true"
            
            #update plex window properties
            linkCount = 0
            while linkCount !=14:
                plexstring = "plexbmc." + str(linkCount)
                link = self.win.getProperty(plexstring + ".title")
                if not link:
                    break
                utils.logMsg(plexstring + ".title --> " + link)
                plexType = self.win.getProperty(plexstring + ".type")
                utils.logMsg(plexstring + ".type --> " + plexType)            

                link = self.win.getProperty(plexstring + ".path")
                utils.logMsg(plexstring + ".path --> " + link)
                
                if hasSecondayMenus == True:
                    recentlink = self.win.getProperty(plexstring + ".recent")
                    progresslink = self.win.getProperty(plexstring + ".viewed")
                else:
                    link = link.replace("mode=1", "mode=0")
                    link = link.replace("mode=2", "mode=0")
                    recentlink = link.replace("/all", "/recentlyAdded")
                    progresslink = link.replace("/all", "/onDeck")
                    self.win.setProperty(plexstring + ".recent", recentlink)
                    self.win.setProperty(plexstring + ".viewed", progresslink)
                    
                self.win.setProperty(plexstring + ".recent.content", utils.getContentPath(recentlink))
                utils.logMsg(plexstring + ".recent --> " + recentlink)       
                
                self.win.setProperty(plexstring + ".viewed.content", utils.getContentPath(progresslink))
                utils.logMsg(plexstring + ".viewed --> " + progresslink)

                linkCount += 1

    def checkNotifications(self):
        
        currentHour = time.strftime("%H")
        
        #weather notifications
        winw = xbmcgui.Window(12600)
        if (winw.getProperty("Alerts.RSS") and winw.getProperty("Current.Condition") and currentHour != self.lastWeatherNotificationCheck):
            dialog = xbmcgui.Dialog()
            dialog.notification(xbmc.getLocalizedString(31294), winw.getProperty("Alerts"), xbmcgui.NOTIFICATION_WARNING, 8000)
            self.lastWeatherNotificationCheck = currentHour
        
        #nextaired notifications
        if (xbmc.getCondVisibility("Skin.HasSetting(EnableNextAiredNotifications) + System.HasAddon(script.tv.show.next.aired)") and currentHour != self.lastNextAiredNotificationCheck):
            if (self.win.getProperty("NextAired.TodayShow")):
                dialog = xbmcgui.Dialog()
                dialog.notification(xbmc.getLocalizedString(31295), self.win.getProperty("NextAired.TodayShow"), xbmcgui.NOTIFICATION_WARNING, 8000)
                self.lastNextAiredNotificationCheck = currentHour
    
    def setWidget(self, containerID):
        self.win.clearProperty("activewidget")
        self.win.clearProperty("customwidgetcontent")
        skinStringContent = ""
        customWidget = False
        
        # workaround for numeric labels (get translated by xbmc)
        skinString = xbmc.getInfoLabel("Container(" + containerID + ").ListItem.Property(submenuVisibility)")
        skinString = skinString.replace("num-","")
        if xbmc.getCondVisibility("Skin.String(widget-" + skinString + ')'):
            skinStringContent = xbmc.getInfoLabel("Skin.String(widget-" + skinString + ')')
        
        # normal method by getting the defaultID
        if skinStringContent == "":
            skinString = xbmc.getInfoLabel("Container(" + containerID + ").ListItem.Property(defaultID)")
            if xbmc.getCondVisibility("Skin.String(widget-" + skinString + ')'):
                skinStringContent = xbmc.getInfoLabel("Skin.String(widget-" + skinString + ')')
           
        if skinStringContent and not "search" in skinStringContent:
            if ("$INFO" in skinStringContent or "Activate" in skinStringContent or ":" in skinStringContent):
                skinStringContent = utils.getContentPath(skinStringContent)
                customWidget = True   
            if customWidget:
                 self.win.setProperty("customwidgetcontent", skinStringContent)
                 self.win.setProperty("activewidget","custom")
            else:
                self.win.clearProperty("customwidgetcontent")
                self.win.setProperty("activewidget",skinStringContent)

        else:
            self.win.clearProperty("activewidget")

    def setSpotlightWidget(self, containerID):
        self.win.clearProperty("spotlightwidgetcontent")
        skinStringContent = ""
        customWidget = False
        
        # workaround for numeric labels (get translated by xbmc)
        skinString = xbmc.getInfoLabel("Container(" + containerID + ").ListItem.Property(submenuVisibility)")
        skinString = skinString.replace("num-","")
        if xbmc.getCondVisibility("Skin.String(spotlightwidget-" + skinString + ')'):
            skinStringContent = xbmc.getInfoLabel("Skin.String(spotlightwidget-" + skinString + ')')
        
        # normal method by getting the defaultID
        if skinStringContent == "":
            skinString = xbmc.getInfoLabel("Container(" + containerID + ").ListItem.Property(defaultID)")
            if xbmc.getCondVisibility("Skin.String(spotlightwidget-" + skinString + ')'):
                skinStringContent = xbmc.getInfoLabel("Skin.String(spotlightwidget-" + skinString + ')')
           
        if skinStringContent and not "search" in skinStringContent:
            if ("$INFO" in skinStringContent or "Activate" in skinStringContent or ":" in skinStringContent):
                skinStringContent = utils.getContentPath(skinStringContent)
                customWidget = True
            self.win.setProperty("spotlightwidgetcontent", skinStringContent)

        else:
            self.win.clearProperty("spotlightwidgetcontent")        