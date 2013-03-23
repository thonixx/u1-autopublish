#!/usr/bin/env python

# Author: Roman Yepishev (roman.yepishev@errormessaging.com)
# This script will immediately publish the files that are uploaded from Ubuntu
# One directories specfified by the user.
# Usage:
# $ ubuntuone-publish-service.py /home/rtg/Public

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
import gobject
import pynotify
import sys
import os
import gtk

class PublishService(object):
    def __init__(self, watched_dirs):

        DBusGMainLoop(set_as_default=True)
        
        self._dirs = []
        for directory in watched_dirs:
            directory = os.path.abspath(directory)
            if os.path.isdir(directory):
                # Creating a trailing '/' for future matching
                self._dirs.append(os.path.join(directory,''))

        # Initializing notification
        pynotify.init("Ubuntu One publish service")
        self._notification = pynotify.Notification(
                "Ubuntu One publish service","")

        # Setting up notification icon
        theme = gtk.icon_theme_get_default()
        pixbuf = theme.load_icon("ubuntuone", 64,
                gtk.ICON_LOOKUP_GENERIC_FALLBACK)
        self._notification.set_icon_from_pixbuf(pixbuf)

        # Setting up dbus handlers and proxies
        bus= dbus.SessionBus()
        public_files_proxy = bus.get_object(
                'com.ubuntuone.SyncDaemon',
                '/publicfiles')
        self._public_files_if = dbus.Interface(public_files_proxy,
                'com.ubuntuone.SyncDaemon.PublicFiles')

        filesystem_proxy = bus.get_object(
                'com.ubuntuone.SyncDaemon',
                '/filesystem')

        self._filesystem_if = dbus.Interface(filesystem_proxy,
                'com.ubuntuone.SyncDaemon.FileSystem')

        bus.add_signal_receiver(
                handler_function=self.on_file_uploaded,
                dbus_interface='com.ubuntuone.SyncDaemon.Status',
                signal_name='UploadFinished')

        bus.add_signal_receiver(
                handler_function=self.on_public_access_changed,
                dbus_interface='com.ubuntuone.SyncDaemon.PublicFiles',
                signal_name='PublicAccessChanged')

    def on_file_uploaded(self, path, info):
        for directory in self._dirs:
            # directory already has trailing separator
            if path.startswith(directory):
                # if /home/user/directory + / matches file path
                # we publish the file
                self.publish_file(path)
                return

    def get_file_info(self, path):
        file_info = self._filesystem_if.get_metadata(path)
        return file_info

    def publish_file(self, path):
        file_info = self.get_file_info(path)
        self._public_files_if.change_public_access(file_info['share_id'],
                file_info['node_id'], True)

    def on_public_access_changed(self, file_info):
        path = file_info['path']
        is_public = file_info['is_public']

        if is_public:
            public_url = file_info['public_url']
            self.notify_published(path, public_url)
	    os.system("echo -n '%s' | xclip" %public_url)
	    os.system("echo -n '%s' | xclip -selection c" %public_url)
        else:
            self.notify_removed(path)

    def notify_published(self, path, public_url):
        title = "File published"
        text = "{0} is published to {1}".format(path, public_url)
        self.notify(title, text)
        pass

    def notify_removed(self, path):
        title = "Public access removed"
        self.notify(title, path)

    def notify(self, title, text):
        self._notification.update(title, text)
        self._notification.show()

def main(watched_dirs):
    publisher = PublishService(watched_dirs)

if __name__ == "__main__":
    watched_dirs = sys.argv[1:]

    if len(watched_dirs) == 0:
        print "Usage: {0} /directory1/ ..."
        sys.exit(1)

    gobject.timeout_add(0, main, sys.argv[1:])
    loop = gobject.MainLoop()
    loop.run()
